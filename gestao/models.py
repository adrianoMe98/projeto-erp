from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.template import Template, Context

class Cliente(models.Model):
    nome_fantasia = models.CharField(max_length=150)
    razao_social = models.CharField(max_length=150, blank=True, null=True)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.CharField(max_length=255, blank=True, null=True, help_text="Endereço completo da sede")
    
    # --- DADOS DO REPRESENTANTE LEGAL ---
    contato_principal = models.CharField(max_length=100, help_text="Nome do Diretor/Administrador")
    nacionalidade = models.CharField(max_length=50, blank=True, null=True, default="brasileiro(a)")
    estado_civil = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: casado(a), solteiro(a)")
    rg = models.CharField(max_length=20, blank=True, null=True, help_text="RG do representante")
    cpf = models.CharField(max_length=18, blank=True, null=True, help_text="CPF do representante")
    
    franquia_horas = models.IntegerField(default=10, help_text="Total de horas mensais contratadas")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_fantasia
        
# --- MÓDULO FINANCEIRO ---
class FinanceiroCliente(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ('PIX', 'PIX'),
        ('BOL', 'Boleto Bancário'),
        ('TRA', 'Transferência (TED/DOC)'),
    ]
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='financeiro')
    valor_mensalidade = models.DecimalField(max_digits=10, decimal_places=2, help_text="Ex: 1500.00")
    dia_vencimento = models.IntegerField(help_text="Dia do mês para vencimento (Ex: 10)")
    forma_pagamento = models.CharField(max_length=3, choices=FORMA_PAGAMENTO_CHOICES, default='PIX')
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Perfil Financeiro"
        verbose_name_plural = "Perfis Financeiros"

    def __str__(self):
        return f"Financeiro - {self.cliente.nome_fantasia}"

# --- MODELO DE CONTRATO DINÂMICO ---
class ModeloContrato(models.Model):
    nome = models.CharField(max_length=150, help_text="Ex: Consultoria Nível 1 - Com RT")
    texto_base = models.TextField(
        help_text="Use variáveis: {{ cliente.nome_fantasia }}, {{ cliente.cnpj }}, {{ financeiro.valor_mensalidade }}, etc."
    )

    class Meta:
        verbose_name = "Modelo de Contrato"
        verbose_name_plural = "Modelos de Contratos"

    def __str__(self):
        return self.nome

# --- CONTRATO DO CLIENTE ---
class Contrato(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contratos')
    modelo = models.ForeignKey(ModeloContrato, on_delete=models.PROTECT, null=True)
    
    data_inicio = models.DateField(default=timezone.now)
    data_vencimento = models.DateField(null=True, blank=True, help_text="Validade padrão de 1 ano")
    
    arquivo_pdf = models.FileField(upload_to='contratos/', blank=True, null=True, help_text="Faça o upload do PDF após o cliente assinar.")
    ativo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.data_vencimento and self.data_inicio:
            self.data_vencimento = self.data_inicio + timedelta(days=365)
        super().save(*args, **kwargs)

    # Função que gera o contrato final mesclando texto com dados do banco
    def texto_renderizado(self):
        if not self.modelo or not self.modelo.texto_base:
            return "Nenhum modelo selecionado ou modelo vazio."
        
        financeiro = getattr(self.cliente, 'financeiro', None)
        template = Template(self.modelo.texto_base)
        context = Context({
            'cliente': self.cliente,
            'financeiro': financeiro,
            'contrato': self,
        })
        return template.render(context)

    def __str__(self):
        return f"Contrato {self.modelo} - {self.cliente.nome_fantasia}"

# --- HISTÓRICO DE PAGAMENTOS ---
class Pagamento(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pago'),
        ('A', 'Aberto / Pendente'),
        ('T', 'Atrasado'), # Corrigido para 'T'
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagamentos')
    referencia = models.CharField(max_length=20, help_text="Ex: Janeiro/2026")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Histórico de Pagamentos"
        ordering = ['-data_vencimento']

    def __str__(self):
        return f"{self.referencia} - {self.cliente.nome_fantasia} ({self.get_status_display()})"