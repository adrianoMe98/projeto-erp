import json
import secrets

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from pagamentos.models import PixCharge
from pagamentos.services.simulator import process_simulator_event
from portal.models import PerfilCliente


def _assert_charge_access(user, charge):
    if user.is_staff:
        return
    try:
        if user.perfil.cliente_id != charge.cliente_id:
            raise PermissionDenied
    except PerfilCliente.DoesNotExist as exc:
        raise PermissionDenied from exc


def _assert_pix_enabled():
    if not settings.PIX_ENABLED:
        raise Http404


@login_required
def charge_detail(request, charge_id):
    _assert_pix_enabled()
    charge = get_object_or_404(PixCharge.objects.select_related("cliente"), pk=charge_id)
    _assert_charge_access(request.user, charge)
    return render(
        request, "pagamentos/charge_detail.html", {"charge": charge, "cliente": charge.cliente}
    )


@login_required
@require_GET
def charge_qr(request, charge_id):
    _assert_pix_enabled()
    charge = get_object_or_404(PixCharge, pk=charge_id)
    _assert_charge_access(request.user, charge)
    image = qrcode.make(charge.pix_copy_paste, image_factory=qrcode.image.svg.SvgPathImage)
    response = HttpResponse(content_type="image/svg+xml")
    image.save(response)
    return response


@csrf_exempt
@require_POST
def simulator_webhook(request):
    _assert_pix_enabled()
    configured_token = settings.PIX_SIMULATOR_WEBHOOK_TOKEN
    received_token = request.headers.get("X-Simulator-Token", "")
    if not configured_token or not secrets.compare_digest(configured_token, received_token):
        return JsonResponse({"error": "unauthorized"}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        event, created = process_simulator_event(payload)
    except PixCharge.DoesNotExist:
        return JsonResponse({"error": "charge_not_found"}, status=404)
    except (ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"status": "processed", "event_id": event.event_id, "new": created})
