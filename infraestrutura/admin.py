from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    VRF,
    EnderecoIP,
    Equipamento,
    GeradorVlanLote,
    HistoricoIPAM,
    SecaoIPAM,
    Subrede,
    Vlan,
)


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "cliente", "ip_gerencia", "ativo")
    list_filter = ("tipo", "ativo", "cliente")
    search_fields = ("nome", "ip_gerencia", "cliente__nome_fantasia")


@admin.register(Vlan)
class VlanAdmin(admin.ModelAdmin):
    list_display = ("vlan_id", "nome", "cliente", "equipamento_origem")
    list_filter = ("cliente",)
    search_fields = ("nome", "vlan_id", "cliente__nome_fantasia")


@admin.register(GeradorVlanLote)
class GeradorVlanLoteAdmin(admin.ModelAdmin):
    list_display = ("nome_base", "vlan_inicial", "vlan_final", "cliente")


@admin.register(SecaoIPAM)
class SecaoIPAMAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "ordem", "descricao")
    list_filter = ("cliente",)
    search_fields = ("nome", "descricao", "cliente__nome_fantasia")


@admin.register(VRF)
class VRFAdmin(admin.ModelAdmin):
    list_display = ("nome", "route_distinguisher", "cliente", "descricao")
    list_filter = ("cliente",)
    search_fields = ("nome", "route_distinguisher", "cliente__nome_fantasia")


@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ("endereco", "hostname", "subrede", "status", "responsavel")
    list_filter = ("status", "subrede__cliente")
    search_fields = ("endereco", "hostname", "descricao", "responsavel", "mac_address")


@admin.register(Subrede)
class SubredeAdmin(admin.ModelAdmin):
    list_display = (
        "prefixo",
        "descricao",
        "cliente",
        "secao",
        "vrf",
        "status",
        "rede_pai",
        "open_ipam",
    )
    list_filter = ("cliente", "secao", "vrf", "status")
    search_fields = ("prefixo", "descricao", "gateway", "localizacao")

    @admin.display(description="IPAM")
    def open_ipam(self, obj):
        url = reverse("ipam:subnet_detail", args=[obj.pk])
        return format_html('<a class="btn btn-sm btn-primary" href="{}">Abrir</a>', url)


@admin.register(HistoricoIPAM)
class HistoricoIPAMAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "acao", "cliente", "resumo", "usuario")
    list_filter = ("acao", "cliente", "criado_em")
    search_fields = ("resumo", "usuario__username")
    readonly_fields = (
        "cliente",
        "usuario",
        "acao",
        "objeto_tipo",
        "objeto_id",
        "resumo",
        "detalhes",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
