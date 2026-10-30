import ipaddress

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

from gestao.models import Cliente


class SecaoIPAM(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="secoes_ipam")
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=250, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Seção IPAM"
        verbose_name_plural = "Seções IPAM"
        ordering = ("cliente__nome_fantasia", "ordem", "nome")
        constraints = [
            models.UniqueConstraint(fields=["cliente", "nome"], name="uniq_secao_ipam_cliente_nome")
        ]

    def __str__(self):
        return f"{self.cliente} · {self.nome}"


class VRF(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="vrfs")
    nome = models.CharField(max_length=100)
    route_distinguisher = models.CharField(
        "Route Distinguisher",
        max_length=50,
        blank=True,
        help_text="Ex.: 65000:100. Deixe vazio para uma tabela lógica sem RD.",
    )
    descricao = models.CharField(max_length=250, blank=True)

    class Meta:
        verbose_name = "VRF"
        verbose_name_plural = "VRFs"
        ordering = ("cliente__nome_fantasia", "nome")
        constraints = [
            models.UniqueConstraint(fields=["cliente", "nome"], name="uniq_vrf_cliente_nome"),
            models.UniqueConstraint(
                fields=["cliente", "route_distinguisher"],
                condition=~models.Q(route_distinguisher=""),
                name="uniq_vrf_cliente_rd_preenchido",
            ),
        ]

    def __str__(self):
        rd = f" ({self.route_distinguisher})" if self.route_distinguisher else ""
        return f"{self.cliente} · {self.nome}{rd}"


class Equipamento(models.Model):
    TIPO_CHOICES = [
        ("R", "Roteador/Borda"),
        ("S", "Switch/Core"),
        ("O", "OLT"),
        ("V", "Servidor/Virtualização"),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    ip_gerencia = models.GenericIPAddressField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "nome"], name="uniq_equipamento_cliente_nome"
            )
        ]

    def __str__(self):
        return self.nome


class Vlan(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    vlan_id = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4094)]
    )
    nome = models.CharField(max_length=100)
    equipamento_origem = models.ForeignKey(
        Equipamento, on_delete=models.SET_NULL, null=True, blank=True
    )
    interface = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Ex: sfp-sfpplus1, gpon 0/1/2, bond0",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cliente", "vlan_id"], name="uniq_vlan_cliente_id"),
            models.CheckConstraint(
                condition=models.Q(vlan_id__gte=1, vlan_id__lte=4094),
                name="vlan_id_entre_1_4094",
            ),
        ]

    def clean(self):
        if self.equipamento_origem and self.equipamento_origem.cliente_id != self.cliente_id:
            raise ValidationError(
                {"equipamento_origem": "O equipamento deve pertencer ao mesmo cliente."}
            )

    def __str__(self):
        return f"VLAN {self.vlan_id} - {self.nome}"


class GeradorVlanLote(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    equipamento_origem = models.ForeignKey(
        Equipamento, on_delete=models.SET_NULL, null=True, blank=True
    )
    vlan_inicial = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4094)], help_text="Ex: 100"
    )
    vlan_final = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4094)], help_text="Ex: 150"
    )
    nome_base = models.CharField(
        max_length=100,
        help_text="Ex: VLAN-CLIENTES (Gerará VLAN-CLIENTES-100, etc)",
    )

    class Meta:
        verbose_name = "Gerar VLANs em Lote"
        verbose_name_plural = "Gerar VLANs em Lote"

    def clean(self):
        errors = {}
        if self.vlan_final < self.vlan_inicial:
            errors["vlan_final"] = "A VLAN final deve ser maior ou igual à inicial."
        if self.vlan_final - self.vlan_inicial + 1 > 512:
            errors["vlan_final"] = "Uma operação pode gerar no máximo 512 VLANs."
        if self.equipamento_origem and self.equipamento_origem.cliente_id != self.cliente_id:
            errors["equipamento_origem"] = "O equipamento deve pertencer ao mesmo cliente."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            Vlan.objects.bulk_create(
                [
                    Vlan(
                        cliente=self.cliente,
                        vlan_id=vid,
                        nome=f"{self.nome_base}-{vid}",
                        equipamento_origem=self.equipamento_origem,
                    )
                    for vid in range(self.vlan_inicial, self.vlan_final + 1)
                ],
                ignore_conflicts=True,
            )


class Subrede(models.Model):
    STATUS_CHOICES = [
        ("A", "Ativa"),
        ("C", "Contêiner"),
        ("R", "Reservada"),
        ("D", "Desativada"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    secao = models.ForeignKey(
        SecaoIPAM,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subredes",
    )
    vrf = models.ForeignKey(
        VRF,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subredes",
        help_text="Vazio representa a tabela de roteamento padrão.",
    )
    rede_pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subredes_filhas",
    )
    prefixo = models.CharField(max_length=45, help_text="Ex: 192.168.100.0/24 ou 2001:db8::/32")
    descricao = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A")
    gateway = models.GenericIPAddressField(null=True, blank=True)
    localizacao = models.CharField(max_length=150, blank=True)
    observacoes = models.TextField(blank=True)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    vlan = models.ForeignKey(Vlan, on_delete=models.SET_NULL, null=True, blank=True)
    interface = models.CharField(
        max_length=100, blank=True, null=True, help_text="Ex: ether2, vlan100"
    )

    class Meta:
        verbose_name = "Subrede"
        verbose_name_plural = "Subredes"
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "prefixo"],
                condition=models.Q(vrf__isnull=True),
                name="uniq_subrede_cliente_prefixo_default",
            ),
            models.UniqueConstraint(
                fields=["cliente", "vrf", "prefixo"],
                condition=models.Q(vrf__isnull=False),
                name="uniq_subrede_cliente_vrf_prefixo",
            ),
        ]

    def clean(self):
        errors = {}
        if self.rede_pai:
            if not self.secao_id:
                self.secao_id = self.rede_pai.secao_id
            if self.vrf_id is None:
                self.vrf_id = self.rede_pai.vrf_id
        try:
            network = ipaddress.ip_network(self.prefixo, strict=False)
            self.prefixo = str(network)
        except ValueError:
            errors["prefixo"] = "Informe um prefixo IPv4 ou IPv6 válido."
            network = None

        if self.equipamento and self.equipamento.cliente_id != self.cliente_id:
            errors["equipamento"] = "O equipamento deve pertencer ao mesmo cliente."
        if self.vlan and self.vlan.cliente_id != self.cliente_id:
            errors["vlan"] = "A VLAN deve pertencer ao mesmo cliente."
        if self.secao and self.secao.cliente_id != self.cliente_id:
            errors["secao"] = "A seção IPAM deve pertencer ao mesmo cliente."
        if self.vrf and self.vrf.cliente_id != self.cliente_id:
            errors["vrf"] = "A VRF deve pertencer ao mesmo cliente."

        if self.gateway and network:
            try:
                gateway = ipaddress.ip_address(self.gateway)
                if gateway.version != network.version or gateway not in network:
                    errors["gateway"] = "O gateway deve pertencer à sub-rede."
                elif (
                    network.version == 4
                    and network.prefixlen <= 30
                    and gateway in {network.network_address, network.broadcast_address}
                ):
                    errors["gateway"] = "Rede e broadcast não podem ser usados como gateway."
                else:
                    self.gateway = str(gateway)
            except ValueError:
                errors["gateway"] = "Informe um gateway IPv4 ou IPv6 válido."

        if self.rede_pai:
            if self.rede_pai_id == self.pk:
                errors["rede_pai"] = "Uma rede não pode ser pai de si própria."
            elif self.rede_pai.cliente_id != self.cliente_id:
                errors["rede_pai"] = "A rede pai deve pertencer ao mesmo cliente."
            elif self.rede_pai.vrf_id != self.vrf_id:
                errors["vrf"] = "A sub-rede deve usar a mesma VRF da rede pai."
            elif self.secao_id and self.rede_pai.secao_id != self.secao_id:
                errors["secao"] = "A sub-rede deve usar a mesma seção da rede pai."
            elif network:
                try:
                    parent = ipaddress.ip_network(self.rede_pai.prefixo, strict=False)
                    if network.version != parent.version or not network.subnet_of(parent):
                        errors["rede_pai"] = "A sub-rede deve estar contida na rede pai."
                    elif network == parent:
                        errors["prefixo"] = "A sub-rede deve ser menor do que a rede pai."
                except ValueError:
                    errors["rede_pai"] = "A rede pai possui prefixo inválido."

            ancestor = self.rede_pai
            visited = set()
            while ancestor:
                if ancestor.pk in visited or (self.pk and ancestor.pk == self.pk):
                    errors["rede_pai"] = "A hierarquia contém um ciclo."
                    break
                visited.add(ancestor.pk)
                ancestor = ancestor.rede_pai

            if network and visited:
                for entry in EnderecoIP.objects.filter(subrede_id__in=visited).only("endereco"):
                    try:
                        address = ipaddress.ip_address(entry.endereco)
                    except ValueError:
                        continue
                    if address.version == network.version and address in network:
                        errors.setdefault(
                            "prefixo",
                            (
                                f"O endereço {entry.endereco} já está cadastrado em uma rede "
                                "ancestral. Mova o endereço antes de criar este bloco."
                            ),
                        )
                        break

        if network and self.pk:
            for child in self.subredes_filhas.only("prefixo", "cliente_id", "secao_id", "vrf_id"):
                try:
                    child_network = ipaddress.ip_network(child.prefixo, strict=False)
                except ValueError:
                    continue
                if child.cliente_id != self.cliente_id:
                    errors.setdefault(
                        "cliente",
                        "O cliente não pode ser alterado enquanto houver sub-redes filhas.",
                    )
                if child.secao_id != self.secao_id:
                    errors.setdefault(
                        "secao", "A seção não pode ser alterada enquanto houver sub-redes filhas."
                    )
                if child.vrf_id != self.vrf_id:
                    errors.setdefault(
                        "vrf", "A VRF não pode ser alterada enquanto houver sub-redes filhas."
                    )
                if child_network.version != network.version or not child_network.subnet_of(network):
                    errors.setdefault(
                        "prefixo",
                        f"A alteração deixaria a sub-rede filha {child.prefixo} fora do bloco pai.",
                    )

            direct_addresses = self.enderecos_ip.only("endereco")
            if self.status == "C" and direct_addresses.exists():
                errors.setdefault(
                    "status",
                    "Um bloco com endereços cadastrados diretamente não pode virar contêiner.",
                )
            for entry in direct_addresses:
                try:
                    address = ipaddress.ip_address(entry.endereco)
                except ValueError:
                    continue
                address_is_special = (
                    network.version == 4
                    and network.prefixlen <= 30
                    and address in {network.network_address, network.broadcast_address}
                )
                if (
                    address.version != network.version
                    or address not in network
                    or address_is_special
                ):
                    errors.setdefault(
                        "prefixo",
                        (
                            f"A alteração tornaria o endereço cadastrado {entry.endereco} "
                            "inválido nesta sub-rede."
                        ),
                    )
                    break

        if network and self.cliente_id and "prefixo" not in errors:
            ancestor_ids = set()
            ancestor = self.rede_pai
            while ancestor and ancestor.pk not in ancestor_ids:
                ancestor_ids.add(ancestor.pk)
                ancestor = ancestor.rede_pai

            candidates = Subrede.objects.filter(
                cliente_id=self.cliente_id, vrf_id=self.vrf_id
            ).exclude(pk=self.pk)
            for other in candidates.only("id", "prefixo", "rede_pai_id"):
                try:
                    other_network = ipaddress.ip_network(other.prefixo, strict=False)
                except ValueError:
                    continue
                if network.version != other_network.version or not network.overlaps(other_network):
                    continue
                if other.pk in ancestor_ids or self._is_ancestor_of(other):
                    continue
                errors["prefixo"] = (
                    f"O prefixo se sobrepõe a {other.prefixo} na mesma VRF sem relação hierárquica."
                )
                break

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.rede_pai:
            if not self.secao_id:
                self.secao_id = self.rede_pai.secao_id
            if not self.vrf_id:
                self.vrf_id = self.rede_pai.vrf_id
        self.full_clean()
        super().save(*args, **kwargs)

    def _is_ancestor_of(self, subnet):
        if not self.pk:
            return False
        visited = set()
        ancestor = subnet.rede_pai
        while ancestor and ancestor.pk not in visited:
            if ancestor.pk == self.pk:
                return True
            visited.add(ancestor.pk)
            ancestor = ancestor.rede_pai
        return False

    def __str__(self):
        return f"{self.prefixo} ({self.descricao or 'Sem descrição'})"

    @property
    def total_ips(self):
        try:
            return ipaddress.ip_network(self.prefixo, strict=False).num_addresses
        except ValueError:
            return 0

    @property
    def versao_ip(self):
        try:
            return ipaddress.ip_network(self.prefixo, strict=False).version
        except ValueError:
            return None

    @property
    def total_utilizavel(self):
        try:
            network = ipaddress.ip_network(self.prefixo, strict=False)
        except ValueError:
            return 0
        if network.version == 4 and network.prefixlen <= 30:
            return max(network.num_addresses - 2, 0)
        return network.num_addresses

    @property
    def ips_em_uso(self):
        return self.enderecos_ip.exclude(status="D").count()

    @property
    def espaco_alocado(self):
        children_total = sum(child.total_ips for child in self.subredes_filhas.all())
        return min(children_total + self.ips_em_uso, self.total_utilizavel)

    @property
    def ips_livres(self):
        return max(self.total_utilizavel - self.espaco_alocado, 0)

    @property
    def percentual_uso(self):
        if not self.total_utilizavel:
            return 0
        return round((self.espaco_alocado / self.total_utilizavel) * 100, 2)


class EnderecoIP(models.Model):
    STATUS_CHOICES = [
        ("A", "Ativo"),
        ("R", "Reservado"),
        ("D", "Desativado"),
    ]
    subrede = models.ForeignKey(Subrede, on_delete=models.PROTECT, related_name="enderecos_ip")
    endereco = models.GenericIPAddressField(help_text="Endereço IP individual")
    hostname = models.CharField(max_length=253, blank=True)
    mac_address = models.CharField("Endereço MAC", max_length=17, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)
    descricao = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A")
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Endereço IP"
        verbose_name_plural = "Endereços IP"
        constraints = [
            models.UniqueConstraint(
                fields=["subrede", "endereco"], name="uniq_endereco_por_subrede"
            )
        ]

    def clean(self):
        try:
            network = ipaddress.ip_network(self.subrede.prefixo, strict=False)
            address = ipaddress.ip_address(self.endereco)
        except (ValueError, Subrede.DoesNotExist):
            raise ValidationError({"endereco": "Endereço ou sub-rede inválidos."}) from None
        if address.version != network.version or address not in network:
            raise ValidationError({"endereco": "O endereço não pertence à sub-rede selecionada."})
        if (
            network.version == 4
            and network.prefixlen <= 30
            and address in {network.network_address, network.broadcast_address}
        ):
            raise ValidationError(
                {"endereco": "Endereços de rede e broadcast não são atribuíveis."}
            )
        if self.subrede.status == "C":
            raise ValidationError(
                {"subrede": "Endereços não podem ser cadastrados diretamente em um contêiner."}
            )

        sibling_subnets = Subrede.objects.filter(
            cliente_id=self.subrede.cliente_id,
            vrf_id=self.subrede.vrf_id,
        ).exclude(pk=self.subrede_id)
        for sibling in sibling_subnets.only("prefixo"):
            try:
                sibling_network = ipaddress.ip_network(sibling.prefixo, strict=False)
                if address in sibling_network:
                    if sibling_network.subnet_of(network):
                        raise ValidationError(
                            {
                                "endereco": (
                                    "O endereço pertence a uma sub-rede filha; "
                                    "cadastre-o no bloco mais específico."
                                )
                            }
                        )
                    errors = EnderecoIP.objects.filter(
                        subrede=sibling, endereco=str(address)
                    ).exclude(pk=self.pk)
                    if errors.exists():
                        raise ValidationError(
                            {"endereco": "O endereço já está registrado em outra sub-rede da VRF."}
                        )
            except ValueError:
                continue
        self.endereco = str(address)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.endereco


class HistoricoIPAM(models.Model):
    ACAO_CHOICES = [
        ("CREATE", "Criação"),
        ("UPDATE", "Alteração"),
        ("SPLIT", "Subdivisão"),
        ("ALLOCATE", "Alocação"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="historico_ipam")
    usuario = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="eventos_ipam"
    )
    acao = models.CharField(max_length=10, choices=ACAO_CHOICES)
    objeto_tipo = models.CharField(max_length=30)
    objeto_id = models.PositiveBigIntegerField(null=True, blank=True)
    resumo = models.CharField(max_length=250)
    detalhes = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico IPAM"
        verbose_name_plural = "Histórico IPAM"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.get_acao_display()} · {self.resumo}"
