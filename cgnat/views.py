from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from cgnat.models import CgnatGeneration
from cgnat.services.report import build_generation_pdf
from portal.models import PerfilCliente


def _assert_access(user, generation, script=False):
    if user.is_staff:
        return
    if script or not generation.disponivel_cliente:
        raise PermissionDenied
    try:
        if user.perfil.cliente_id != generation.plan.cliente_id:
            raise PermissionDenied
    except PerfilCliente.DoesNotExist as exc:
        raise PermissionDenied from exc


@login_required
def report_download(request, generation_id):
    generation = get_object_or_404(
        CgnatGeneration.objects.select_related("plan", "plan__cliente"), pk=generation_id
    )
    _assert_access(request.user, generation)
    response = HttpResponse(build_generation_pdf(generation), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="cgnat-{generation.pk}.pdf"'
    return response


@login_required
def script_download(request, generation_id):
    generation = get_object_or_404(CgnatGeneration, pk=generation_id)
    _assert_access(request.user, generation, script=True)
    response = HttpResponse(generation.content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="cgnat-{generation.pk}.{generation.file_extension}"'
    )
    return response
