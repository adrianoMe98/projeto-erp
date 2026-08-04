from django.db import models
from gestao.models import Cliente
from infraestrutura.models import Equipamento
from django.utils.timezone import now
from django.utils.html import mark_safe

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('A', 'Aberto'),
        ('E', 'Em Andamento'),
        ('G', 'Aguardando Cliente'),
        ('C', 'Concluído'),
        ('X', 'Cancelado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='tickets')
    titulo = models.CharField(max_length=200, help_text="Resumo do problema ou solicitação")
    descricao = models.TextField(help_text="Descrição detalhada do chamado")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # --- CAMPOS NOVOS DO CRONÔMETRO ---
    tempo_acumulado_segundos = models.PositiveIntegerField(default=0, editable=False)
    hora_inicio_cronometro = models.DateTimeField(blank=True, null=True, editable=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        gerar_apontamento = False
        
        if not is_new:
            old_status = Ticket.objects.get(pk=self.pk).status

        if self.status == 'E' and old_status != 'E':
            self.hora_inicio_cronometro = now()

        if old_status == 'E' and self.status != 'E':
            if self.hora_inicio_cronometro:
                delta = now() - self.hora_inicio_cronometro
                self.tempo_acumulado_segundos += int(delta.total_seconds())
                self.hora_inicio_cronometro = None
                
        if self.status == 'C' and old_status != 'C':
            if self.tempo_acumulado_segundos > 0:
                gerar_apontamento = True
                
        if self.status == 'X':
            self.tempo_acumulado_segundos = 0
            self.hora_inicio_cronometro = None

        super().save(*args, **kwargs)

        if gerar_apontamento:
            horas_decimais = round(self.tempo_acumulado_segundos / 3600.0, 2)
            if horas_decimais > 0:
                self.apontamentos.create(
                    descricao_atividade="Fechamento automático. Tempo contabilizado pelo sistema.",
                    tempo_gasto=horas_decimais
                )
            self.tempo_acumulado_segundos = 0
            super().save(update_fields=['tempo_acumulado_segundos'])

    @property
    def visor_cronometro(self):
        total_segundos = self.tempo_acumulado_segundos
        rodando = "false"
        estado = "⏹️ PARADO"
        cor = "#6c757d"
        
        if self.status == 'E':
            if self.hora_inicio_cronometro:
                delta = now() - self.hora_inicio_cronometro
                total_segundos += int(delta.total_seconds())
            rodando = "true"
            estado = "▶️ RODANDO"
            cor = "#28a745"
        elif self.status == 'G':
            estado = "⏸️ PAUSADO"
            cor = "#ffc107"
            
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        segundos = total_segundos % 60
        
        tempo_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        
        # HTML e JavaScript injetados diretamente (à prova de cache!)
        html = f'''
            <span id="cronometro-display" style="font-size: 14px; font-weight: bold; background: {cor}; color: #fff; padding: 5px 10px; border-radius: 4px; display: inline-block; min-width: 180px; text-align: center; text-shadow: 1px 1px 1px rgba(0,0,0,0.3);">
                ⏳ {tempo_str} ({estado})
            </span>
            <script>
                (function() {{
                    var display = document.getElementById('cronometro-display');
                    // Limpa intervalos anteriores para evitar aceleração dupla do relógio
                    if (window.cronInterval) clearInterval(window.cronInterval);
                    
                    if (display && "{rodando}" === "true") {{
                        var segundosTotais = {total_segundos};
                        window.cronInterval = setInterval(function() {{
                            segundosTotais++;
                            var h = Math.floor(segundosTotais / 3600).toString().padStart(2, '0');
                            var m = Math.floor((segundosTotais % 3600) / 60).toString().padStart(2, '0');
                            var s = (segundosTotais % 60).toString().padStart(2, '0');
                            display.innerHTML = '⏳ ' + h + ':' + m + ':' + s + ' (▶️ RODANDO)';
                        }}, 1000);
                    }}
                }})();
            </script>
        '''
        return mark_safe(html)

    def __str__(self):
        return f"#{self.id} - {self.titulo} ({self.cliente.nome_fantasia})"

class Apontamento(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='apontamentos')
    data = models.DateField(auto_now_add=True)
    descricao_atividade = models.TextField(help_text="O que foi feito nesta intervenção?")
    tempo_gasto = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tempo em horas (Ex: 1.5 para 1h30min)")

    def __str__(self):
        return f"{self.tempo_gasto}h - {self.ticket.titulo}"