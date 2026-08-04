from django.db import models
from django.contrib.auth.models import User
from gestao.models import Cliente

class PerfilCliente(models.Model):
    # Relaciona 1 Usuário a 1 Cliente
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='usuarios_acesso')

    def __str__(self):
        return f"Acesso: {self.usuario.username} -> {self.cliente.nome_fantasia}"