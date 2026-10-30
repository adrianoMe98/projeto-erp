from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestao.models import Cliente
from helpdesk.models import Ticket
from infraestrutura.models import Equipamento


class TicketTimerTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP Helpdesk",
            cnpj="00.000.000/0005-01",
            contato_principal="Responsável",
        )

    def test_closing_running_ticket_creates_time_entry(self):
        start = timezone.now()
        with patch("helpdesk.models.now", return_value=start):
            ticket = Ticket.objects.create(
                cliente=self.cliente, titulo="Teste", descricao="Descrição", status="E"
            )
        ticket.status = "C"
        with patch("helpdesk.models.now", return_value=start + timedelta(hours=1)):
            ticket.save()
        entry = ticket.apontamentos.get()
        self.assertEqual(str(entry.tempo_gasto), "1.00")
        ticket.refresh_from_db()
        self.assertEqual(ticket.tempo_acumulado_segundos, 0)

    def test_equipment_must_belong_to_ticket_customer(self):
        other = Cliente.objects.create(
            nome_fantasia="Outro Helpdesk",
            cnpj="00.000.000/0005-02",
            contato_principal="Outro",
        )
        equipment = Equipamento.objects.create(cliente=other, nome="OLT", tipo="O")
        ticket = Ticket(
            cliente=self.cliente,
            equipamento=equipment,
            titulo="Falha",
            descricao="Descrição da falha",
        )
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_timer_markup_uses_class_without_inline_script(self):
        ticket = Ticket.objects.create(
            cliente=self.cliente, titulo="Teste", descricao="Descrição", status="A"
        )
        markup = str(ticket.visor_cronometro)
        self.assertIn('class="cronometro-display"', markup)
        self.assertNotIn("<script", markup)
