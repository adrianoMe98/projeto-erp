from django.contrib import admin
from django.urls import path
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from .models import Cliente, FinanceiroCliente, ModeloContrato, Contrato, Pagamento

# Injeta o financeiro diretamente dentro da tela do cliente
class FinanceiroInline(admin.StackedInline):
    model = FinanceiroCliente
    can_delete = False

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'cnpj', 'franquia_horas', 'ativo')
    inlines = [FinanceiroInline] # Aparece junto ao editar o cliente

@admin.register(ModeloContrato)
class ModeloContratoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    # Atualizamos a descrição para mostrar as novas variáveis disponíveis na tela do Admin
    description = "Variáveis do Representante: {{ cliente.contato_principal }}, {{ cliente.nacionalidade }}, {{ cliente.estado_civil }}, {{ cliente.rg }}, {{ cliente.cpf }}, {{ cliente.endereco }}"

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'modelo', 'data_inicio', 'data_vencimento', 'ativo', 'btn_gerar_pdf')
    list_filter = ('modelo', 'ativo')
    
    # 1. Registra a URL customizada para a tela de impressão
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:contrato_id>/imprimir/', self.admin_site.admin_view(self.imprimir_view), name='imprimir-contrato'),
        ]
        return custom_urls + urls

    # 2. Cria o botão na listagem do painel Admin
    def btn_gerar_pdf(self, obj):
        if obj.modelo:
            return format_html('<a class="btn btn-sm btn-info" href="{}/imprimir/" target="_blank" style="color: white;"><i class="fas fa-print"></i> Visualizar / Salvar PDF</a>', obj.id)
        return "-"
    btn_gerar_pdf.short_description = "Documento"

    # 3. View que renderiza o contrato limpo em folha A4
    def imprimir_view(self, request, contrato_id):
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        context = {
            'contrato': contrato,
            'cliente': contrato.cliente,
        }
        return render(request, 'admin/gestao/contrato/imprimir.html', context)

@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'referencia', 'valor', 'data_vencimento', 'status', 'data_pagamento')
    list_filter = ('status', 'cliente')