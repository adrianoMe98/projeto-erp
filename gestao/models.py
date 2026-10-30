from datetime import date
from decimal import Decimal

import bleach
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.template import Context, Template
from django.utils import timezone


def validate_pdf_upload(upload):
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError("O PDF deve ter no máximo 10 MB.")
    position = upload.tell() if hasattr(upload, "tell") else None
    try:
        upload.seek(0)
        if upload.read(5) != b"%PDF-":
            raise ValidationError("O arquivo enviado não possui uma assinatura PDF válida.")
    finally:
        if position is not None:
            upload.seek(position)


class Cliente(models.Model):
    nome_fantasia = models.CharField(max_length=150)
    razao_social = models.CharField(max_length=150, blank=True, null=True)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.CharField(
        max_length=255, blank=True, null=True, help_text="Endereço completo da sede"
    )
    contato_principal = models.CharField(max_length=100, help_text="Nome do Diretor/Administrador")
    nacionalidade = models.CharField(max_length=50, blank=True, null=True, default="brasileiro(a)")
    estado_civil = models.CharField(
        max_length=50, blank=True, null=True, help_text="Ex: casado(a), solteiro(a)"
    )
    rg = models.CharField(max_length=20, blank=True, null=True, help_text="RG do representante")
    cpf = models.CharField(max_length=18, blank=True, null=True, help_text="CPF do representante")
    franquia_horas = models.PositiveIntegerField(
        default=10, help_text="Total de horas mensais contratadas"
    )
    ativo = models.BooleanField(default=True)

    @property
    def horas_consumidas_mes(self):
        hoje = timezone.localdate()
        total = self.tickets.filter(
            apontamentos__data__year=hoje.year,
            apontamentos__data__month=hoje.month,
        ).aggregate(total=Sum("apontamentos__tempo_gasto"))["total"]
        return total or Decimal("0.00")

    @property
    def saldo_horas(self):
        return Decimal(self.franquia_horas) - self.horas_consumidas_mes

    def __str__(self):
        return self.nome_fantasia


class FinanceiroCliente(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ("PIX", "PIX"),
        ("BOL", "Boleto Bancário"),
        ("TRA", "Transferência (TED/DOC)"),
    ]
    cliente = models.OneToOneField(Cliente, on_delete=models.PROTECT, related_name="financeiro")
    valor_mensalidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Ex: 1500.00",
    )
    dia_vencimento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Dia do mês para vencimento (Ex: 10)",
    )
    forma_pagamento = models.CharField(max_length=3, choices=FORMA_PAGAMENTO_CHOICES, default="PIX")
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Perfil Financeiro"
        verbose_name_plural = "Perfis Financeiros"

    def __str__(self):
        return f"Financeiro - {self.cliente.nome_fantasia}"


class ModeloContrato(models.Model):
    nome = models.CharField(max_length=150, help_text="Ex: Consultoria Nível 1 - Com RT")
    texto_base = models.TextField(
        help_text="Use variáveis: {{ cliente.nome_fantasia }}, {{ cliente.cnpj }}, "
        "{{ financeiro.valor_mensalidade }}, etc."
    )

    class Meta:
        verbose_name = "Modelo de Contrato"
        verbose_name_plural = "Modelos de Contratos"

    def __str__(self):
        return self.nome


class Contrato(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="contratos")
    modelo = models.ForeignKey(ModeloContrato, on_delete=models.PROTECT, null=True)
    data_inicio = models.DateField(default=timezone.now)
    data_vencimento = models.DateField(null=True, blank=True, help_text="Validade padrão de 1 ano")
    arquivo_pdf = models.FileField(
        upload_to="contratos/",
        blank=True,
        null=True,
        validators=[validate_pdf_upload],
        help_text="PDF assinado, com no máximo 10 MB.",
    )
    ativo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.data_vencimento and self.data_inicio:
            try:
                self.data_vencimento = self.data_inicio.replace(year=self.data_inicio.year + 1)
            except ValueError:
                self.data_vencimento = date(self.data_inicio.year + 1, 2, 28)
        super().save(*args, **kwargs)

    def texto_renderizado(self):
        if not self.modelo or not self.modelo.texto_base:
            return "Nenhum modelo selecionado ou modelo vazio."
        financeiro = getattr(self.cliente, "financeiro", None)
        rendered = Template(self.modelo.texto_base).render(
            Context(
                {
                    "cliente": self.cliente,
                    "financeiro": financeiro,
                    "contrato": self,
                }
            )
        )
        return bleach.clean(
            rendered,
            tags=[
                "p",
                "br",
                "strong",
                "b",
                "em",
                "i",
                "u",
                "ul",
                "ol",
                "li",
                "h1",
                "h2",
                "h3",
                "h4",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
            ],
            attributes={},
            strip=True,
        )

    def __str__(self):
        return f"Contrato {self.modelo} - {self.cliente.nome_fantasia}"


class Pagamento(models.Model):
    STATUS_CHOICES = [
        ("P", "Pago"),
        ("A", "Aberto / Pendente"),
        ("T", "Atrasado"),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pagamentos")
    referencia = models.CharField(max_length=20, help_text="Ex: Janeiro/2026")
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A")

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Histórico de Pagamentos"
        ordering = ["-data_vencimento"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "referencia"], name="uniq_pagamento_cliente_referencia"
            )
        ]

    def clean(self):
        if self.status == "P" and not self.data_pagamento:
            raise ValidationError({"data_pagamento": "Informe a data do pagamento."})
        if self.data_pagamento and self.status != "P":
            raise ValidationError({"status": "Pagamentos com data devem estar como pagos."})

    def __str__(self):
        return f"{self.referencia} - {self.cliente.nome_fantasia} ({self.get_status_display()})"
