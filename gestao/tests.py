from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestao.models import Cliente, Contrato, ModeloContrato, Pagamento
from helpdesk.models import Apontamento, Ticket


class ManagementRulesTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP Gestão",
            cnpj="00.000.000/0006-01",
            contato_principal="Responsável",
            franquia_horas=10,
        )

    def test_monthly_balance_uses_time_entries(self):
        ticket = Ticket.objects.create(
            cliente=self.cliente, titulo="Atendimento", descricao="Descrição"
        )
        Apontamento.objects.create(
            ticket=ticket, descricao_atividade="Ajuste", tempo_gasto=Decimal("2.50")
        )
        self.assertEqual(self.cliente.horas_consumidas_mes, Decimal("2.50"))
        self.assertEqual(self.cliente.saldo_horas, Decimal("7.50"))

    def test_contract_template_removes_executable_html(self):
        model = ModeloContrato.objects.create(
            nome="Teste",
            texto_base="<strong>{{ cliente.nome_fantasia }}</strong><script>alert(1)</script>",
        )
        contract = Contrato.objects.create(cliente=self.cliente, modelo=model)
        rendered = contract.texto_renderizado()
        self.assertIn("<strong>ISP Gestão</strong>", rendered)
        self.assertNotIn("<script", rendered)

    def test_leap_day_contract_gets_valid_anniversary(self):
        contract = Contrato.objects.create(cliente=self.cliente, data_inicio=date(2028, 2, 29))
        self.assertEqual(contract.data_vencimento, date(2029, 2, 28))

    def test_paid_financial_entry_requires_payment_date(self):
        payment = Pagamento(
            cliente=self.cliente,
            referencia="Outubro/2026",
            valor=Decimal("100.00"),
            data_vencimento=date(2026, 10, 10),
            status="P",
        )
        with self.assertRaises(ValidationError):
            payment.full_clean()
