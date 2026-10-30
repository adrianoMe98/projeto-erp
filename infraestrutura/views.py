import ipaddress
from collections import defaultdict
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from gestao.models import Cliente
from portal.models import PerfilCliente

from .forms import EnderecoIPForm, SubnetSplitForm, SubredeForm
from .ipam import allocate_subnets, free_subnets, next_free_address, visual_map
from .models import VRF, EnderecoIP, HistoricoIPAM, SecaoIPAM, Subrede


def staff_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def _network_key(subnet):
    try:
        network = ipaddress.ip_network(subnet.prefixo, strict=False)
        return (network.version, int(network.network_address), network.prefixlen)
    except ValueError:
        return (99, 0, 0)


def _tree_rows(subnets):
    items = list(subnets)
    item_ids = {item.pk for item in items}
    children = defaultdict(list)
    roots = []
    for subnet in items:
        if subnet.rede_pai_id in item_ids:
            children[subnet.rede_pai_id].append(subnet)
        else:
            roots.append(subnet)

    def root_key(item):
        return (
            item.cliente.nome_fantasia.lower(),
            item.secao.nome.lower() if item.secao else "",
            item.vrf.nome.lower() if item.vrf else "",
            _network_key(item),
        )

    rows = []

    def walk(subnet, depth):
        rows.append({"subnet": subnet, "depth": depth, "indent": min(depth, 8) * 22})
        for child in sorted(children[subnet.pk], key=_network_key):
            walk(child, depth + 1)

    for root in sorted(roots, key=root_key):
        walk(root, 0)
    return rows


def _format_count(value):
    return f"{value:,}".replace(",", ".")


def _breadcrumbs(subnet):
    result = []
    visited = set()
    current = subnet
    while current and current.pk not in visited:
        result.append(current)
        visited.add(current.pk)
        current = current.rede_pai
    return list(reversed(result))


@staff_required
def dashboard(request):
    subnets = Subrede.objects.select_related(
        "cliente", "secao", "vrf", "rede_pai", "vlan", "equipamento"
    ).prefetch_related("subredes_filhas", "enderecos_ip")
    query = request.GET.get("q", "").strip()
    client_id = request.GET.get("cliente", "").strip()
    section_id = request.GET.get("secao", "").strip()
    vrf_id = request.GET.get("vrf", "").strip()
    family = request.GET.get("familia", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        subnets = subnets.filter(
            Q(prefixo__icontains=query)
            | Q(descricao__icontains=query)
            | Q(gateway__icontains=query)
            | Q(localizacao__icontains=query)
            | Q(vlan__nome__icontains=query)
            | Q(equipamento__nome__icontains=query)
            | Q(enderecos_ip__endereco__icontains=query)
            | Q(enderecos_ip__hostname__icontains=query)
            | Q(enderecos_ip__descricao__icontains=query)
        ).distinct()
    if client_id:
        subnets = subnets.filter(cliente_id=client_id)
    if section_id:
        subnets = subnets.filter(secao_id=section_id)
    if vrf_id == "default":
        subnets = subnets.filter(vrf__isnull=True)
    elif vrf_id:
        subnets = subnets.filter(vrf_id=vrf_id)
    if family == "4":
        subnets = subnets.exclude(prefixo__contains=":")
    elif family == "6":
        subnets = subnets.filter(prefixo__contains=":")
    if status:
        subnets = subnets.filter(status=status)

    rows = _tree_rows(subnets)
    page = Paginator(rows, 50).get_page(request.GET.get("page"))
    all_subnets = Subrede.objects.all()
    context = {
        "page": page,
        "clients": Cliente.objects.filter(ativo=True).order_by("nome_fantasia"),
        "sections": SecaoIPAM.objects.select_related("cliente"),
        "vrfs": VRF.objects.select_related("cliente"),
        "status_choices": Subrede.STATUS_CHOICES,
        "filters": {
            "q": query,
            "cliente": client_id,
            "secao": section_id,
            "vrf": vrf_id,
            "familia": family,
            "status": status,
        },
        "stats": {
            "total": all_subnets.count(),
            "ipv4": all_subnets.exclude(prefixo__contains=":").count(),
            "ipv6": all_subnets.filter(prefixo__contains=":").count(),
            "addresses": EnderecoIP.objects.exclude(status="D").count(),
        },
    }
    return render(request, "ipam/dashboard.html", context)


@staff_required
def subnet_detail(request, subnet_id):
    subnet = get_object_or_404(
        Subrede.objects.select_related(
            "cliente", "secao", "vrf", "rede_pai", "vlan", "equipamento"
        ).prefetch_related("subredes_filhas", "enderecos_ip"),
        pk=subnet_id,
    )
    children = sorted(
        subnet.subredes_filhas.select_related("vlan", "equipamento").all(), key=_network_key
    )
    addresses = subnet.enderecos_ip.order_by("endereco")
    address_page = Paginator(addresses, 50).get_page(request.GET.get("page"))
    context = {
        "subnet": subnet,
        "children": children,
        "address_page": address_page,
        "breadcrumbs": _breadcrumbs(subnet),
        "visual_cells": visual_map(subnet),
        "total_display": _format_count(subnet.total_utilizavel),
        "allocated_display": _format_count(subnet.espaco_alocado),
        "free_display": _format_count(subnet.ips_livres),
        "history": HistoricoIPAM.objects.filter(
            cliente=subnet.cliente, objeto_tipo="subrede", objeto_id=subnet.pk
        )[:10],
    }
    return render(request, "ipam/subnet_detail.html", context)


@staff_required
def subnet_create(request):
    parent = None
    parent_id = request.GET.get("parent") or request.POST.get("rede_pai")
    if parent_id:
        parent = get_object_or_404(Subrede, pk=parent_id)
    initial = {}
    if parent:
        initial = {
            "cliente": parent.cliente,
            "secao": parent.secao,
            "vrf": parent.vrf,
            "rede_pai": parent,
        }
    form = SubredeForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        subnet = form.save()
        HistoricoIPAM.objects.create(
            cliente=subnet.cliente,
            usuario=request.user,
            acao="CREATE",
            objeto_tipo="subrede",
            objeto_id=subnet.pk,
            resumo=f"Sub-rede {subnet.prefixo} criada",
            detalhes={"prefixo": subnet.prefixo, "descricao": subnet.descricao or ""},
        )
        messages.success(request, f"Sub-rede {subnet.prefixo} criada com segurança.")
        return redirect("ipam:subnet_detail", subnet_id=subnet.pk)
    return render(
        request,
        "ipam/subnet_form.html",
        {"form": form, "parent": parent, "action_title": "Adicionar sub-rede"},
    )


@staff_required
def subnet_edit(request, subnet_id):
    subnet = get_object_or_404(Subrede, pk=subnet_id)
    original = {
        "prefixo": subnet.prefixo,
        "descricao": subnet.descricao or "",
        "status": subnet.status,
        "gateway": subnet.gateway or "",
    }
    form = SubredeForm(request.POST or None, instance=subnet)
    if request.method == "POST" and form.is_valid():
        subnet = form.save()
        changed = {
            field: {"antes": original[field], "depois": value}
            for field, value in {
                "prefixo": subnet.prefixo,
                "descricao": subnet.descricao or "",
                "status": subnet.status,
                "gateway": subnet.gateway or "",
            }.items()
            if original[field] != value
        }
        HistoricoIPAM.objects.create(
            cliente=subnet.cliente,
            usuario=request.user,
            acao="UPDATE",
            objeto_tipo="subrede",
            objeto_id=subnet.pk,
            resumo=f"Sub-rede {subnet.prefixo} alterada",
            detalhes={"alteracoes": changed},
        )
        messages.success(request, f"Sub-rede {subnet.prefixo} atualizada.")
        return redirect("ipam:subnet_detail", subnet_id=subnet.pk)
    return render(
        request,
        "ipam/subnet_form.html",
        {
            "form": form,
            "parent": subnet.rede_pai,
            "subnet": subnet,
            "action_title": "Editar sub-rede",
        },
    )


@staff_required
def subnet_split(request, subnet_id):
    parent = get_object_or_404(
        Subrede.objects.select_related("cliente", "secao", "vrf"), pk=subnet_id
    )
    form = SubnetSplitForm(request.POST or None, parent=parent)
    preview = []
    if request.method == "POST" and form.is_valid():
        try:
            preview = free_subnets(
                parent, form.cleaned_data["new_prefix"], form.cleaned_data["quantity"]
            )
            if request.POST.get("action") == "allocate":
                created = allocate_subnets(
                    parent=parent,
                    new_prefix=form.cleaned_data["new_prefix"],
                    quantity=form.cleaned_data["quantity"],
                    description=form.cleaned_data["description"],
                    user=request.user,
                )
                messages.success(request, f"{len(created)} sub-rede(s) alocada(s) com sucesso.")
                return redirect("ipam:subnet_detail", subnet_id=parent.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "ipam/subnet_split.html",
        {"parent": parent, "form": form, "preview": preview},
    )


@staff_required
def address_create(request, subnet_id):
    subnet = get_object_or_404(Subrede.objects.select_related("cliente", "vrf"), pk=subnet_id)
    suggested = next_free_address(subnet)
    form = EnderecoIPForm(request.POST or None, subnet=subnet, suggested_address=suggested)
    if request.method == "POST" and form.is_valid():
        address = form.save()
        HistoricoIPAM.objects.create(
            cliente=subnet.cliente,
            usuario=request.user,
            acao="ALLOCATE",
            objeto_tipo="endereco_ip",
            objeto_id=address.pk,
            resumo=f"Endereço {address.endereco} alocado em {subnet.prefixo}",
            detalhes={"subrede_id": subnet.pk, "hostname": address.hostname},
        )
        messages.success(request, f"Endereço {address.endereco} cadastrado.")
        return redirect("ipam:subnet_detail", subnet_id=subnet.pk)
    return render(
        request,
        "ipam/address_form.html",
        {"subnet": subnet, "form": form, "suggested": suggested},
    )


@staff_required
def address_edit(request, subnet_id, address_id):
    subnet = get_object_or_404(Subrede.objects.select_related("cliente", "vrf"), pk=subnet_id)
    address = get_object_or_404(EnderecoIP, pk=address_id, subrede=subnet)
    form = EnderecoIPForm(request.POST or None, subnet=subnet, instance=address)
    if request.method == "POST" and form.is_valid():
        address = form.save()
        HistoricoIPAM.objects.create(
            cliente=subnet.cliente,
            usuario=request.user,
            acao="UPDATE",
            objeto_tipo="endereco_ip",
            objeto_id=address.pk,
            resumo=f"Endereço {address.endereco} alterado",
            detalhes={"subrede_id": subnet.pk, "hostname": address.hostname},
        )
        messages.success(request, f"Endereço {address.endereco} atualizado.")
        return redirect("ipam:subnet_detail", subnet_id=subnet.pk)
    return render(
        request,
        "ipam/address_form.html",
        {"subnet": subnet, "form": form, "suggested": address.endereco, "address": address},
    )


@login_required
def portal_subnet_detail(request, subnet_id):
    try:
        client_id = request.user.perfil.cliente_id
    except PerfilCliente.DoesNotExist as exc:
        raise PermissionDenied from exc
    subnet = get_object_or_404(
        Subrede.objects.select_related("cliente", "secao", "vrf", "vlan", "equipamento"),
        pk=subnet_id,
        cliente_id=client_id,
    )
    context = {
        "cliente": subnet.cliente,
        "subnet": subnet,
        "children": sorted(subnet.subredes_filhas.all(), key=_network_key),
        "addresses": subnet.enderecos_ip.exclude(status="D").order_by("endereco")[:250],
        "breadcrumbs": _breadcrumbs(subnet),
        "total_display": _format_count(subnet.total_utilizavel),
        "allocated_display": _format_count(subnet.espaco_alocado),
        "free_display": _format_count(subnet.ips_livres),
    }
    return render(request, "portal/ipam_detail.html", context)
