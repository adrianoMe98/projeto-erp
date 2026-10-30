import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from gestao.models import Cliente, Pagamento


class PixCharge(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pix_charges")
    pagamento = models.OneToOneField(
        Pagamento,
        on_delete=models.PROTECT,
        related_name="pix_charge",
        null=True,
        blank=True,
    )
    txid = models.CharField(max_length=35, unique=True, editable=False)
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    descricao = models.CharField(max_length=140)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=30, default="simulator", editable=False)
    provider_charge_id = models.CharField(max_length=80, blank=True, editable=False)
    pix_copy_paste = models.TextField(blank=True, editable=False)
    expires_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrança Pix"
        verbose_name_plural = "Cobranças Pix"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cliente", "status", "-created_at"], name="pix_cliente_status_idx")
        ]

    def clean(self):
        errors = {}
        if self.pagamento and self.pagamento.cliente_id != self.cliente_id:
            errors["pagamento"] = "O lançamento financeiro deve pertencer ao mesmo cliente."
        if self.pagamento and self.valor != self.pagamento.valor:
            errors["valor"] = "O valor deve ser igual ao lançamento financeiro vinculado."
        if self.status == self.Status.PAID and not self.paid_at:
            errors["status"] = "Cobranças pagas precisam da data de confirmação."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.txid:
            self.txid = uuid.uuid4().hex.upper()
        if not self.provider_charge_id:
            self.provider_charge_id = self.txid
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=1)
        if not self.pix_copy_paste:
            self.pix_copy_paste = (
                f"PIX-SIMULADO|TXID={self.txid}|VALOR={self.valor:.2f}|NAO-PAGAVEL"
            )
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.status == self.Status.PENDING and self.expires_at <= timezone.now()

    def __str__(self):
        return f"{self.txid} - {self.cliente.nome_fantasia} - R$ {self.valor}"


class PixWebhookEvent(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    charge = models.ForeignKey(PixCharge, on_delete=models.PROTECT, related_name="webhook_events")
    event_type = models.CharField(max_length=40)
    payload = models.JSONField()
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de webhook Pix"
        verbose_name_plural = "Eventos de webhook Pix"
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.event_id} - {self.event_type}"
