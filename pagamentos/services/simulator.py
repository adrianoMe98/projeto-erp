import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from pagamentos.models import PixCharge, PixWebhookEvent


@transaction.atomic
def process_simulator_event(payload):
    event_id = str(payload.get("event_id", "")).strip()
    event_type = str(payload.get("event_type", "")).strip()
    txid = str(payload.get("txid", "")).strip()
    if not event_id or not event_type or not txid:
        raise ValueError("event_id, event_type e txid são obrigatórios.")

    charge = PixCharge.objects.select_for_update().get(txid=txid)
    existing = PixWebhookEvent.objects.filter(event_id=event_id).first()
    if existing:
        return existing, False
    if event_type != "pix.paid":
        raise ValueError("Tipo de evento não suportado pelo simulador.")
    try:
        amount = Decimal(str(payload.get("amount")))
    except (InvalidOperation, TypeError):
        raise ValueError("Valor do evento inválido.") from None
    if amount != charge.valor:
        raise ValueError("O valor do evento não corresponde à cobrança.")

    paid_at = parse_datetime(str(payload.get("paid_at", ""))) or timezone.now()
    if timezone.is_naive(paid_at):
        paid_at = timezone.make_aware(paid_at)

    if charge.status != PixCharge.Status.PAID:
        charge.status = PixCharge.Status.PAID
        charge.paid_at = paid_at
        charge.save(update_fields=["status", "paid_at", "updated_at"])
        if charge.pagamento_id:
            pagamento = charge.pagamento
            pagamento.status = "P"
            pagamento.data_pagamento = timezone.localdate(paid_at)
            pagamento.save(update_fields=["status", "data_pagamento"])

    event = PixWebhookEvent.objects.create(
        event_id=event_id,
        charge=charge,
        event_type=event_type,
        payload=payload,
    )
    return event, True


def simulate_payment(charge):
    return process_simulator_event(
        {
            "event_id": f"sim-{uuid.uuid4()}",
            "event_type": "pix.paid",
            "txid": charge.txid,
            "amount": str(charge.valor),
            "paid_at": timezone.now().isoformat(),
        }
    )
