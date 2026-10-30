import ipaddress
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from cgnat.services.allocation import MAX_SUBSCRIBERS, build_mappings, calculate_capacity
from gestao.models import Cliente

INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:+-]{1,32}$")
SHARED_SPACE = ipaddress.ip_network("100.64.0.0/10")


class CgnatPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cgnat_plans")
    nome = models.CharField(max_length=120)
    rede_privada = models.CharField(max_length=43, help_text="Bloco RFC 6598, ex: 100.64.0.0/24")
    rede_publica = models.CharField(max_length=43, help_text="Bloco IPv4 público usado na tradução")
    porta_inicial = models.PositiveIntegerField(
        default=1024, validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )
    porta_final = models.PositiveIntegerField(
        default=65535, validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )
    portas_por_assinante = models.PositiveIntegerField(
        default=512, validators=[MinValueValidator(64), MaxValueValidator(64512)]
    )
    limite_assinantes = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_SUBSCRIBERS)],
        help_text="Vazio utiliza todos os hosts da rede privada.",
    )
    interface_saida = models.CharField(max_length=32, default="WAN")
    incluir_icmp = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plano CGNAT"
        verbose_name_plural = "Planos CGNAT"
        constraints = [
            models.UniqueConstraint(fields=["cliente", "nome"], name="uniq_cgnat_cliente_nome")
        ]

    def clean(self):
        errors = {}
        try:
            private_network = ipaddress.ip_network(self.rede_privada, strict=False)
            self.rede_privada = str(private_network)
            if private_network.version != 4:
                errors["rede_privada"] = "CGNAT desta versão aceita somente IPv4."
            elif not private_network.subnet_of(SHARED_SPACE):
                errors["rede_privada"] = "Use o espaço compartilhado RFC 6598 (100.64.0.0/10)."
        except ValueError:
            errors["rede_privada"] = "Informe uma rede IPv4 válida."
            private_network = None

        try:
            public_network = ipaddress.ip_network(self.rede_publica, strict=False)
            self.rede_publica = str(public_network)
            if public_network.version != 4:
                errors["rede_publica"] = "A rede de saída deve ser IPv4."
        except ValueError:
            errors["rede_publica"] = "Informe uma rede IPv4 válida."
            public_network = None

        if self.porta_final < self.porta_inicial:
            errors["porta_final"] = "A porta final deve ser maior ou igual à inicial."
        if not INTERFACE_PATTERN.fullmatch(self.interface_saida or ""):
            errors["interface_saida"] = "Use apenas letras, números e os caracteres _ . : + -."

        if private_network and public_network:
            if private_network.overlaps(public_network):
                errors["rede_publica"] = "As redes privada e pública não podem se sobrepor."
            try:
                build_mappings(
                    private_network,
                    public_network,
                    self.porta_inicial,
                    self.porta_final,
                    self.portas_por_assinante,
                    self.limite_assinantes,
                )
            except ValueError as exc:
                errors["limite_assinantes"] = str(exc)
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def mappings(self):
        return build_mappings(
            self.rede_privada,
            self.rede_publica,
            self.porta_inicial,
            self.porta_final,
            self.portas_por_assinante,
            self.limite_assinantes,
        )

    @property
    def capacidade_total(self):
        network = ipaddress.ip_network(self.rede_publica, strict=False)
        return calculate_capacity(
            network, self.porta_inicial, self.porta_final, self.portas_por_assinante
        )[1]

    def __str__(self):
        return f"{self.nome} - {self.cliente.nome_fantasia}"


class CgnatGeneration(models.Model):
    class Target(models.TextChoices):
        ROUTEROS6 = "routeros6", "MikroTik RouterOS 6"
        ROUTEROS7 = "routeros7", "MikroTik RouterOS 7"
        IPTABLES = "iptables", "Linux iptables"
        NFTABLES = "nftables", "Linux nftables"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(CgnatPlan, on_delete=models.PROTECT, related_name="generations")
    target = models.CharField(max_length=20, choices=Target.choices)
    content = models.TextField()
    sha256 = models.CharField(max_length=64, editable=False)
    mapping_snapshot = models.JSONField(default=list)
    summary = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False
    )
    disponivel_cliente = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Configuração CGNAT gerada"
        verbose_name_plural = "Configurações CGNAT geradas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["plan", "target", "-created_at"], name="cgnat_plan_target_idx")
        ]

    @property
    def file_extension(self):
        return "rsc" if self.target.startswith("routeros") else "sh"

    def __str__(self):
        return f"{self.plan.nome} - {self.get_target_display()} - {self.created_at:%d/%m/%Y %H:%M}"
