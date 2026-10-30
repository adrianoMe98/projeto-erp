import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from gestao.models import Cliente, Pagamento
from pagamentos.models import PixCharge, PixWebhookEvent
from portal.models import PerfilCliente


@override_settings(PIX_ENABLED=True, PIX_SIMULATOR_WEBHOOK_TOKEN="token-de-teste")
class PixSimulatorTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP Pix",
            cnpj="00.000.000/0002-01",
            contato_principal="Responsável",
        )
        self.pagamento = Pagamento.objects.create(
            cliente=self.cliente,
            referencia="Setembro/2026",
            valor=Decimal("150.00"),
            data_vencimento="2026-09-10",
        )
        self.charge = PixCharge.objects.create(
            cliente=self.cliente,
            pagamento=self.pagamento,
            valor=Decimal("150.00"),
            descricao="Mensalidade de setembro",
        )
        self.url = reverse("pagamentos:simulator_webhook")
        self.payload = {
            "event_id": "evt-001",
            "event_type": "pix.paid",
            "txid": self.charge.txid,
            "amount": "150.00",
            "paid_at": "2026-09-03T12:00:00Z",
        }

    def test_webhook_requires_token(self):
        response = self.client.post(
            self.url, data=json.dumps(self.payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_webhook_confirms_charge_and_financial_entry(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            HTTP_X_SIMULATOR_TOKEN="token-de-teste",
        )
        self.assertEqual(response.status_code, 200)
        self.charge.refresh_from_db()
        self.pagamento.refresh_from_db()
        self.assertEqual(self.charge.status, PixCharge.Status.PAID)
        self.assertEqual(self.pagamento.status, "P")
        self.assertEqual(str(self.pagamento.data_pagamento), "2026-09-03")

    def test_webhook_is_idempotent(self):
        for _ in range(2):
            self.client.post(
                self.url,
                data=json.dumps(self.payload),
                content_type="application/json",
                HTTP_X_SIMULATOR_TOKEN="token-de-teste",
            )
        self.assertEqual(PixWebhookEvent.objects.filter(event_id="evt-001").count(), 1)

    def test_rejects_wrong_amount(self):
        self.payload["amount"] = "149.99"
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            HTTP_X_SIMULATOR_TOKEN="token-de-teste",
        )
        self.assertEqual(response.status_code, 400)

    def test_customer_can_only_access_own_charge(self):
        other = Cliente.objects.create(
            nome_fantasia="Outro",
            cnpj="00.000.000/0002-02",
            contato_principal="Outro",
        )
        user = get_user_model().objects.create_user("outro-pix", password="senha-teste")
        PerfilCliente.objects.create(usuario=user, cliente=other)
        self.client.force_login(user)
        response = self.client.get(reverse("pagamentos:detail", args=[self.charge.pk]))
        self.assertEqual(response.status_code, 403)

    def test_qr_is_svg_and_explicitly_simulated(self):
        user = get_user_model().objects.create_user("cliente-pix", password="senha-teste")
        PerfilCliente.objects.create(usuario=user, cliente=self.cliente)
        self.client.force_login(user)
        response = self.client.get(reverse("pagamentos:qr", args=[self.charge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn("NAO-PAGAVEL", self.charge.pix_copy_paste)


@override_settings(PIX_ENABLED=False)
class DisabledPixTests(TestCase):
    def test_simulator_webhook_is_not_exposed(self):
        response = self.client.post(
            reverse("pagamentos:simulator_webhook"), data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
