from django.conf import settings
from django.db import models

from gestao.models import Cliente


class PerfilCliente(models.Model):
    # Relaciona 1 Usuário a 1 Cliente
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="usuarios_acesso")

    def __str__(self):
        return f"Acesso: {self.usuario.username} -> {self.cliente.nome_fantasia}"
