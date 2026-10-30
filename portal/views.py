from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from cgnat.models import CgnatGeneration
from gestao.models import Contrato, Pagamento
from helpdesk.models import Ticket
from infraestrutura.models import Equipamento, Subrede, Vlan
from pagamentos.models import PixCharge
from portal.forms import NovoTicketForm, UnifiedAuthenticationForm
from portal.models import PerfilCliente


class UnifiedLoginView(LoginView):
    authentication_form = UnifiedAuthenticationForm
    template_name = "portal/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        return response

    def get_success_url(self):
        requested_url = self.get_redirect_url()
        is_safe = requested_url and url_has_allowed_host_and_scheme(
            requested_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        if is_safe and (not requested_url.startswith("/admin/") or self.request.user.is_staff):
            return requested_url
        if self.request.user.is_staff:
            return reverse("admin:index")
        if PerfilCliente.objects.filter(usuario=self.request.user).exists():
            return reverse("dashboard")
        return reverse("sem_acesso")


def admin_login_redirect(request):
    next_url = request.GET.get("next", reverse("admin:index"))
    return redirect(f"{reverse('login')}?{urlencode({'next': next_url})}")


@login_required
def sem_acesso(request):
    return render(request, "portal/sem_acesso.html", status=403)


def _subnet_rows(cliente):
    subnets = list(Subrede.objects.filter(cliente=cliente).order_by("prefixo"))
    children = defaultdict(list)
    by_id = {subnet.id: subnet for subnet in subnets}
    for subnet in subnets:
        children[subnet.rede_pai_id].append(subnet)

    rows = []
    visited = set()

    def walk(subnet, depth):
        if subnet.id in visited:
            return
        visited.add(subnet.id)
        rows.append({"subnet": subnet, "depth": depth})
        for child in children[subnet.id]:
            walk(child, depth + 1)

    for root in children[None]:
        walk(root, 0)
    for subnet_id, subnet in by_id.items():
        if subnet_id not in visited:
            walk(subnet, 0)
    return rows


@login_required
def dashboard(request):
    try:
        perfil = request.user.perfil
    except PerfilCliente.DoesNotExist:
        if request.user.is_staff:
            return redirect("admin:index")
        return redirect("sem_acesso")

    cliente = perfil.cliente
    context = {
        "cliente": cliente,
        "tickets": Ticket.objects.filter(cliente=cliente).order_by("-data_abertura"),
        "equipamentos": Equipamento.objects.filter(cliente=cliente),
        "vlans": Vlan.objects.filter(cliente=cliente)
        .select_related("equipamento_origem")
        .order_by("vlan_id"),
        "subnet_rows": _subnet_rows(cliente),
        "financeiro": getattr(cliente, "financeiro", None),
        "contratos": Contrato.objects.filter(cliente=cliente, ativo=True)
        .select_related("modelo")
        .order_by("-data_inicio"),
        "pagamentos": Pagamento.objects.filter(cliente=cliente).order_by("-data_vencimento"),
        "cgnat_reports": CgnatGeneration.objects.filter(
            plan__cliente=cliente, disponivel_cliente=True
        )
        .select_related("plan")
        .order_by("-created_at")[:20],
        "pix_charges": (
            PixCharge.objects.filter(cliente=cliente).order_by("-created_at")[:20]
            if settings.PIX_ENABLED
            else PixCharge.objects.none()
        ),
    }
    return render(request, "portal/dashboard.html", context)


@login_required
def novo_ticket(request):
    try:
        cliente = request.user.perfil.cliente
    except PerfilCliente.DoesNotExist:
        return redirect("sem_acesso")

    form = NovoTicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.cliente = cliente
        ticket.status = "A"
        ticket.save()
        messages.success(request, f"Chamado #{ticket.pk} registrado com sucesso.")
        return redirect("dashboard")

    return render(
        request,
        "portal/novo_ticket.html",
        {"form": form, "cliente": cliente},
    )


@login_required
def contrato_download(request, contrato_id):
    contrato = get_object_or_404(
        Contrato.objects.select_related("cliente"), pk=contrato_id, ativo=True
    )
    if not request.user.is_staff:
        try:
            if request.user.perfil.cliente_id != contrato.cliente_id:
                raise PermissionDenied
        except PerfilCliente.DoesNotExist as exc:
            raise PermissionDenied from exc

    if not contrato.arquivo_pdf:
        raise Http404("Contrato sem arquivo assinado.")
    try:
        stream = contrato.arquivo_pdf.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Arquivo não encontrado.") from exc
    filename = Path(contrato.arquivo_pdf.name).name
    return FileResponse(stream, as_attachment=True, filename=filename)
