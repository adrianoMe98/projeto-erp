from django.contrib import admin
from .models import PerfilCliente

@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cliente')
    list_filter = ('cliente',)
    search_fields = ('usuario__username', 'cliente__nome_fantasia')