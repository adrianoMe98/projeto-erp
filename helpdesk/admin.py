from django.contrib import admin
from .models import Ticket, Apontamento

class ApontamentoInline(admin.TabularInline):
    model = Apontamento
    extra = 1

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    # Adicionamos o visor_cronometro aqui na lista principal se quiser ver de fora:
    list_display = ('id', 'titulo', 'cliente', 'status', 'visor_cronometro', 'data_abertura')
    list_filter = ('status', 'cliente')
    search_fields = ('titulo', 'descricao')
    # autocomplete_fields = ['cliente', 'equipamento']
    
    # Isso faz o campo aparecer DENTRO do cadastro do ticket, apenas para leitura:
    readonly_fields = ('visor_cronometro',) 
    
    inlines = [ApontamentoInline]

    class Media:
        js = ('helpdesk/js/cronometro.js',)