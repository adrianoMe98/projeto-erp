from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from cgnat.models import CgnatGeneration, CgnatPlan
from cgnat.services.allocation import build_mappings
from cgnat.services.generators import create_generation
from gestao.models import Cliente
from portal.models import PerfilCliente


class AllocationTests(TestCase):
    def test_allocates_non_overlapping_port_blocks(self):
        mappings = build_mappings("100.64.0.0/29", "198.51.100.10/32", 1024, 65535, 1024)
        self.assertEqual(len(mappings), 6)
        self.assertEqual(mappings[0].port_start, 1024)
        self.assertEqual(mappings[1].port_start, 2048)
        self.assertLess(mappings[0].port_end, mappings[1].port_start)

    def test_rejects_insufficient_capacity(self):
        with self.assertRaises(ValueError):
            build_mappings("100.64.0.0/24", "198.51.100.1/32", 60000, 65535, 1024)


class GenerationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP Teste",
            cnpj="00.000.000/0001-01",
            contato_principal="Responsável",
        )
        self.plan = CgnatPlan.objects.create(
            cliente=self.cliente,
            nome="Borda 1",
            rede_privada="100.64.0.0/29",
            rede_publica="198.51.100.10/32",
            portas_por_assinante=1024,
            interface_saida="sfp1",
        )

    def test_rejects_private_network_outside_rfc6598(self):
        self.plan.rede_privada = "10.0.0.0/24"
        with self.assertRaises(ValidationError):
            self.plan.full_clean()

    def test_generates_all_targets(self):
        expected = {
            CgnatGeneration.Target.ROUTEROS6: "RouterOS 6",
            CgnatGeneration.Target.ROUTEROS7: "RouterOS 7",
            CgnatGeneration.Target.IPTABLES: "iptables -t nat",
            CgnatGeneration.Target.NFTABLES: "table ip erp_cgnat",
        }
        for target, marker in expected.items():
            generation = create_generation(self.plan, target)
            self.assertIn(marker, generation.content)
            self.assertEqual(len(generation.mapping_snapshot), 6)
            self.assertEqual(len(generation.sha256), 64)

    def test_client_can_download_own_pdf_but_not_script(self):
        generation = create_generation(self.plan, CgnatGeneration.Target.ROUTEROS7)
        user = get_user_model().objects.create_user("cliente", password="senha-teste")
        PerfilCliente.objects.create(usuario=user, cliente=self.cliente)
        self.client.force_login(user)

        report = self.client.get(reverse("cgnat:report", args=[generation.pk]))
        script = self.client.get(reverse("cgnat:script", args=[generation.pk]))
        self.assertEqual(report.status_code, 200)
        self.assertTrue(report.content.startswith(b"%PDF-"))
        self.assertEqual(script.status_code, 403)

    def test_client_cannot_download_another_customer_report(self):
        generation = create_generation(self.plan, CgnatGeneration.Target.ROUTEROS7)
        other = Cliente.objects.create(
            nome_fantasia="Outro ISP",
            cnpj="00.000.000/0001-02",
            contato_principal="Outro",
        )
        user = get_user_model().objects.create_user("outro", password="senha-teste")
        PerfilCliente.objects.create(usuario=user, cliente=other)
        self.client.force_login(user)
        response = self.client.get(reverse("cgnat:report", args=[generation.pk]))
        self.assertEqual(response.status_code, 403)
