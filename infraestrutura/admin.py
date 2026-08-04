from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.html import format_html
import ipaddress

from .models import Equipamento, Vlan, GeradorVlanLote, Subrede, EnderecoIP

# --- ADMINS SIMPLES ---
@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'cliente', 'ip_gerencia', 'ativo')
    list_filter = ('tipo', 'ativo', 'cliente')

@admin.register(Vlan)
class VlanAdmin(admin.ModelAdmin):
    list_display = ('vlan_id', 'nome', 'cliente', 'equipamento_origem')
    list_filter = ('cliente',)

@admin.register(GeradorVlanLote)
class GeradorVlanLoteAdmin(admin.ModelAdmin):
    list_display = ('nome_base', 'vlan_inicial', 'vlan_final', 'cliente')

@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ('endereco', 'subrede', 'status', 'descricao')
    list_filter = ('status', 'subrede')

# --- ADMIN DE SUBREDE COM CALCULADORA E MAPA IPAM ---
@admin.register(Subrede)
class SubredeAdmin(admin.ModelAdmin):
    list_display = ('prefixo', 'descricao', 'cliente', 'rede_pai', 'btn_subdividir', 'btn_mapa')
    list_filter = ('cliente', 'rede_pai')
    search_fields = ('prefixo', 'descricao')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:subrede_id>/subdividir/', self.admin_site.admin_view(self.subdividir_view), name='subdividir-subrede'),
            path('<int:subrede_id>/mapa/', self.admin_site.admin_view(self.mapa_view), name='mapa-subrede'),
        ]
        return custom_urls + urls

    def btn_subdividir(self, obj):
        return format_html('<a class="btn btn-sm btn-info" href="{}/subdividir/" style="color: white;"><i class="fas fa-cut"></i> Fatiar</a>', obj.id)
    btn_subdividir.short_description = "Subdividir"

    def btn_mapa(self, obj):
        try:
            rede = ipaddress.ip_network(obj.prefixo, strict=False)
            # Mostra o mapa apenas para redes /22 ou menores
            if rede.prefixlen >= 22:
                return format_html('<a class="btn btn-sm btn-warning" href="{}/mapa/" style="color: black;"><i class="fas fa-th"></i> Mapa IP</a>', obj.id)
        except:
            pass
        return "-"
    btn_mapa.short_description = "Visualizar"

    # --- Lógica 1: O Mapa Visual ---
    def mapa_view(self, request, subrede_id):
        obj = get_object_or_404(Subrede, pk=subrede_id)
        rede = ipaddress.ip_network(obj.prefixo, strict=False)
        
        ips_cadastrados = {ip.endereco: ip for ip in EnderecoIP.objects.filter(subrede=obj)}
        grid_ips = []
        
        for ip in rede:
            ip_str = str(ip)
            if ip == rede.network_address:
                grid_ips.append({'ip': ip_str, 'cor': 'preto', 'desc': 'Endereço de Rede (Inutilizável)'})
            elif ip == rede.broadcast_address:
                grid_ips.append({'ip': ip_str, 'cor': 'preto', 'desc': 'Broadcast (Inutilizável)'})
            elif ip_str in ips_cadastrados:
                registro = ips_cadastrados[ip_str]
                cor = 'vermelho' if registro.status == 'A' else 'amarelo'
                grid_ips.append({'ip': ip_str, 'cor': cor, 'desc': registro.descricao or 'Em uso'})
            else:
                grid_ips.append({'ip': ip_str, 'cor': 'verde', 'desc': 'Disponível para uso'})

        context = dict(
            self.admin_site.each_context(request),
            obj=obj,
            rede_atual=rede,
            total_ips=rede.num_addresses,
            grid_ips=grid_ips
        )
        return render(request, 'admin/infraestrutura/subrede/mapa.html', context)

    # --- Lógica 2: Calculadora de Subredes (Fatiamento) ---
    def subdividir_view(self, request, subrede_id):
        obj = get_object_or_404(Subrede, pk=subrede_id)
        
        try:
            rede_atual = ipaddress.ip_network(obj.prefixo, strict=False)
        except ValueError:
            messages.error(request, "O prefixo atual desta rede é inválido.")
            return redirect('admin:infraestrutura_subrede_changelist')

        if request.method == 'POST':
            novo_prefixo = int(request.POST.get('novo_prefixo'))
            
            limite = 32 if rede_atual.version == 4 else 128
            if novo_prefixo <= rede_atual.prefixlen or novo_prefixo > limite:
                messages.error(request, "Máscara de subdivisão inválida.")
            else:
                subredes_geradas = list(rede_atual.subnets(new_prefix=novo_prefixo))
                novos_objetos = []
                
                for sub in subredes_geradas:
                    novos_objetos.append(
                        Subrede(
                            cliente=obj.cliente,
                            rede_pai=obj,
                            prefixo=str(sub),
                            descricao=f"Sub-bloco de {obj.prefixo}",
                            equipamento=obj.equipamento,
                            vlan=obj.vlan
                        )
                    )
                
                Subrede.objects.bulk_create(novos_objetos)
                messages.success(request, f"Rede {obj.prefixo} fatiada com sucesso! {len(novos_objetos)} novos blocos /{novo_prefixo} foram criados.")
                return redirect('admin:infraestrutura_subrede_changelist')

        prefixos_validos = range(rede_atual.prefixlen + 1, 33) if rede_atual.version == 4 else range(rede_atual.prefixlen + 1, 129)

        context = dict(
            self.admin_site.each_context(request),
            opts=self.model._meta,
            obj=obj,
            rede_atual=rede_atual,
            prefixos_validos=prefixos_validos
        )
        return render(request, 'admin/infraestrutura/subrede/subdividir.html', context)