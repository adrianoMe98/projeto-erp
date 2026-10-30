from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils.html import format_html
from django.utils.timezone import now

from gestao.models import Cliente
from infraestrutura.models import Equipamento


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("A", "Aberto"),
        ("E", "Em Andamento"),
        ("G", "Aguardando Cliente"),
        ("C", "Concluído"),
        ("X", "Cancelado"),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="tickets")
    titulo = models.CharField(max_length=200, help_text="Resumo do problema ou solicitação")
    descricao = models.TextField(help_text="Descrição detalhada do chamado")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A")
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    tempo_acumulado_segundos = models.PositiveIntegerField(default=0, editable=False)
    hora_inicio_cronometro = models.DateTimeField(blank=True, null=True, editable=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["cliente", "status", "-data_abertura"], name="ticket_cliente_status_idx"
            )
        ]

    def clean(self):
        if self.equipamento and self.equipamento.cliente_id != self.cliente_id:
            raise ValidationError(
                {"equipamento": "O equipamento deve pertencer ao mesmo cliente do chamado."}
            )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        with transaction.atomic():
            old_status = None
            if not is_new:
                previous = Ticket.objects.select_for_update().get(pk=self.pk)
                old_status = previous.status
                self.tempo_acumulado_segundos = previous.tempo_acumulado_segundos
                self.hora_inicio_cronometro = previous.hora_inicio_cronometro

            timestamp = now()
            if self.status == "E" and old_status != "E":
                self.hora_inicio_cronometro = timestamp

            if old_status == "E" and self.status != "E" and self.hora_inicio_cronometro:
                delta = timestamp - self.hora_inicio_cronometro
                self.tempo_acumulado_segundos += max(int(delta.total_seconds()), 0)
                self.hora_inicio_cronometro = None

            gerar_apontamento = (
                self.status == "C" and old_status != "C" and self.tempo_acumulado_segundos > 0
            )
            if self.status == "X":
                self.tempo_acumulado_segundos = 0
                self.hora_inicio_cronometro = None

            super().save(*args, **kwargs)

            if gerar_apontamento:
                horas = (Decimal(self.tempo_acumulado_segundos) / Decimal(3600)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if horas > 0:
                    self.apontamentos.create(
                        descricao_atividade=(
                            "Fechamento automático. Tempo contabilizado pelo sistema."
                        ),
                        tempo_gasto=horas,
                    )
                self.tempo_acumulado_segundos = 0
                super().save(update_fields=["tempo_acumulado_segundos"])

    @property
    def visor_cronometro(self):
        total_segundos = self.tempo_acumulado_segundos
        rodando = self.status == "E" and self.hora_inicio_cronometro is not None
        estado = "PARADO"
        cor = "#6c757d"
        if rodando:
            delta = now() - self.hora_inicio_cronometro
            total_segundos += max(int(delta.total_seconds()), 0)
            estado = "RODANDO"
            cor = "#28a745"
        elif self.status == "G":
            estado = "PAUSADO"
            cor = "#ffc107"

        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        segundos = total_segundos % 60
        tempo = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        return format_html(
            '<span class="cronometro-display" data-running="{}" data-seconds="{}" '
            'style="font-weight:bold;background:{};color:#fff;padding:5px 10px;border-radius:4px">'
            "⏳ {} ({})</span>",
            str(rodando).lower(),
            total_segundos,
            cor,
            tempo,
            estado,
        )

    def __str__(self):
        return f"#{self.id} - {self.titulo} ({self.cliente.nome_fantasia})"


class Apontamento(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="apontamentos")
    data = models.DateField(auto_now_add=True)
    descricao_atividade = models.TextField(help_text="O que foi feito nesta intervenção?")
    tempo_gasto = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Tempo em horas (Ex: 1.5 para 1h30min)",
    )

    def __str__(self):
        return f"{self.tempo_gasto}h - {self.ticket.titulo}"
