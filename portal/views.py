from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from helpdesk.models import Ticket
from infraestrutura.models import Equipamento, Vlan, Subrede 
from gestao.models import Cliente, FinanceiroCliente, Contrato, Pagamento

@login_required 
def dashboard(request):
    try:
        perfil = request.user.perfil
        cliente = perfil.cliente
        tickets = Ticket.objects.filter(cliente=cliente).order_by('-data_abertura')
        
        equipamentos = Equipamento.objects.filter(cliente=cliente)
        vlans = Vlan.objects.filter(cliente=cliente).order_by('vlan_id')
        blocos_ip_raizes = Subrede.objects.filter(cliente=cliente, rede_pai__isnull=True).order_by('prefixo')
        
        # --- DADOS: FINANCEIRO E CONTRATOS ---
        financeiro = getattr(cliente, 'financeiro', None)
        contratos = Contrato.objects.filter(cliente=cliente, ativo=True).order_by('-data_inicio')
        pagamentos = Pagamento.objects.filter(cliente=cliente).order_by('-data_vencimento')
        
    except:
        cliente = None
        tickets = []
        equipamentos = []
        vlans = []
        blocos_ip = []
        financeiro = None
        contratos = []
        pagamentos = []

    context = {
        'cliente': cliente,
        'tickets': tickets,
        'equipamentos': equipamentos,
        'vlans': vlans,
        'blocos_ip_raizes': blocos_ip_raizes, # Atualizado aqui!
        'financeiro': financeiro,
        'contratos': contratos,
        'pagamentos': pagamentos,
    }
    return render(request, 'portal/dashboard.html', context)

@login_required
def novo_ticket(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        
        try:
            cliente = request.user.perfil.cliente
            Ticket.objects.create(
                cliente=cliente,
                titulo=titulo,
                descricao=descricao,
                status='A'
            )
            return redirect('dashboard')
        except:
            pass

    return render(request, 'portal/novo_ticket.html')

def custom_logout(request):
    logout(request)
    return redirect('login')