from django.db import models
from gestao.models import Cliente
import ipaddress

class Equipamento(models.Model):
    TIPO_CHOICES = [
        ('R', 'Roteador/Borda'),
        ('S', 'Switch/Core'),
        ('O', 'OLT'),
        ('V', 'Servidor/Virtualização'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    ip_gerencia = models.GenericIPAddressField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class Vlan(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    vlan_id = models.IntegerField()
    nome = models.CharField(max_length=100)
    equipamento_origem = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    interface = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: sfp-sfpplus1, gpon 0/1/2, bond0")

    def __str__(self):
        return f"VLAN {self.vlan_id} - {self.nome}"

class GeradorVlanLote(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    equipamento_origem = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    vlan_inicial = models.IntegerField(help_text="Ex: 100")
    vlan_final = models.IntegerField(help_text="Ex: 150")
    nome_base = models.CharField(max_length=100, help_text="Ex: VLAN-CLIENTES (Gerará VLAN-CLIENTES-100, etc)")

    class Meta:
        verbose_name = "Gerar VLANs em Lote"
        verbose_name_plural = "Gerar VLANs em Lote"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for vid in range(self.vlan_inicial, self.vlan_final + 1):
            Vlan.objects.get_or_create(
                cliente=self.cliente,
                vlan_id=vid,
                defaults={
                    'nome': f"{self.nome_base}-{vid}",
                    'equipamento_origem': self.equipamento_origem
                }
            )

# --- MOTOR IPAM (Subrede + EnderecoIP) ---

class Subrede(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    rede_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subredes_filhas')
    prefixo = models.CharField(max_length=45, help_text="Ex: 192.168.100.0/24 ou 2001:db8::/32")
    descricao = models.CharField(max_length=200, blank=True, null=True)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    vlan = models.ForeignKey(Vlan, on_delete=models.SET_NULL, null=True, blank=True)
    interface = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: ether2, vlan100")

    class Meta:
        verbose_name = "Subrede"
        verbose_name_plural = "Subredes"
        unique_together = ('cliente', 'prefixo')

    def __str__(self):
        return f"{self.prefixo} ({self.descricao or 'Sem descrição'})"

    @property
    def total_ips(self):
        try:
            rede = ipaddress.ip_network(self.prefixo, strict=False)
            return rede.num_addresses
        except ValueError:
            return 0

    @property
    def ips_em_uso(self):
        return self.enderecos_ip.count()

    @property
    def ips_livres(self):
        return self.total_ips - self.ips_em_uso

class EnderecoIP(models.Model):
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('R', 'Reservado'),
        ('D', 'Desativado'),
    ]
    subrede = models.ForeignKey(Subrede, on_delete=models.CASCADE, related_name='enderecos_ip')
    endereco = models.GenericIPAddressField(help_text="Endereço IP individual")
    descricao = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')

    class Meta:
        verbose_name = "Endereço IP"
        verbose_name_plural = "Endereços IP"

    def __str__(self):
        return self.endereco