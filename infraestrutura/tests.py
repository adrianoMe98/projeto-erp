from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from gestao.models import Cliente
from infraestrutura.ipam import allocate_subnets, free_subnets, next_free_address, visual_map
from infraestrutura.models import VRF, EnderecoIP, Equipamento, SecaoIPAM, Subrede, Vlan
from portal.models import PerfilCliente


class InfrastructureValidationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP Infra",
            cnpj="00.000.000/0004-01",
            contato_principal="Responsável",
        )
        self.other = Cliente.objects.create(
            nome_fantasia="Outro Infra",
            cnpj="00.000.000/0004-02",
            contato_principal="Outro",
        )

    def test_vlan_range_and_tenant_are_validated(self):
        invalid = Vlan(cliente=self.cliente, vlan_id=4095, nome="Inválida")
        with self.assertRaises(ValidationError):
            invalid.full_clean()
        equipment = Equipamento.objects.create(cliente=self.other, nome="Borda", tipo="R")
        cross_tenant = Vlan(
            cliente=self.cliente, vlan_id=100, nome="Cliente", equipamento_origem=equipment
        )
        with self.assertRaises(ValidationError):
            cross_tenant.full_clean()

    def test_invalid_prefix_is_rejected(self):
        with self.assertRaises(ValidationError):
            Subrede.objects.create(cliente=self.cliente, prefixo="não-é-rede")

    def test_child_must_be_inside_parent(self):
        root = Subrede.objects.create(cliente=self.cliente, prefixo="10.0.0.0/24")
        with self.assertRaises(ValidationError):
            Subrede.objects.create(cliente=self.cliente, rede_pai=root, prefixo="192.0.2.0/24")

    def test_ip_must_belong_to_subnet_and_not_be_broadcast(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="10.0.0.0/24")
        with self.assertRaises(ValidationError):
            EnderecoIP.objects.create(subrede=subnet, endereco="192.0.2.1")
        with self.assertRaises(ValidationError):
            EnderecoIP.objects.create(subrede=subnet, endereco="10.0.0.255")

    def test_ipv6_large_map_is_rejected_without_iteration(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="2001:db8::/64")
        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "senha")
        self.client.force_login(admin)
        response = self.client.get(reverse("ipam:subnet_detail", args=[subnet.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "administrados por prefixos")
        self.assertNotContains(response, 'class="ip-cell')

    def test_subdivision_has_safe_limit(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="100.64.0.0/10")
        admin = get_user_model().objects.create_superuser("admin2", "admin2@example.com", "senha")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("ipam:subnet_split", args=[subnet.pk]),
            {"new_prefix": "32", "quantity": "257", "action": "allocate"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "menor ou igual a 256")
        self.assertEqual(subnet.subredes_filhas.count(), 0)


class IPAMDomainTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="ISP IPAM",
            cnpj="00.000.000/0005-01",
            contato_principal="NOC",
        )
        self.other = Cliente.objects.create(
            nome_fantasia="Outro IPAM",
            cnpj="00.000.000/0005-02",
            contato_principal="NOC 2",
        )
        self.section = SecaoIPAM.objects.create(cliente=self.cliente, nome="Backbone")
        self.vrf = VRF.objects.create(
            cliente=self.cliente, nome="Clientes", route_distinguisher="65000:10"
        )

    def test_same_prefix_is_allowed_in_different_vrfs(self):
        other_vrf = VRF.objects.create(cliente=self.cliente, nome="Gerência")
        Subrede.objects.create(cliente=self.cliente, vrf=self.vrf, prefixo="10.0.0.0/24")
        duplicate = Subrede.objects.create(
            cliente=self.cliente, vrf=other_vrf, prefixo="10.0.0.0/24"
        )
        self.assertEqual(duplicate.prefixo, "10.0.0.0/24")

    def test_unrelated_overlap_in_same_vrf_is_rejected(self):
        Subrede.objects.create(cliente=self.cliente, vrf=self.vrf, prefixo="10.0.0.0/24")
        with self.assertRaises(ValidationError):
            Subrede.objects.create(cliente=self.cliente, vrf=self.vrf, prefixo="10.0.0.128/25")

    def test_child_inherits_section_and_vrf(self):
        parent = Subrede.objects.create(
            cliente=self.cliente,
            secao=self.section,
            vrf=self.vrf,
            prefixo="10.20.0.0/16",
            status="C",
        )
        child = Subrede.objects.create(
            cliente=self.cliente, rede_pai=parent, prefixo="10.20.1.0/24"
        )
        self.assertEqual(child.secao, self.section)
        self.assertEqual(child.vrf, self.vrf)

    def test_ipv6_allocator_skips_used_prefix_without_enumerating_space(self):
        parent = Subrede.objects.create(
            cliente=self.cliente,
            secao=self.section,
            vrf=self.vrf,
            prefixo="2001:db8::/32",
            status="C",
        )
        Subrede.objects.create(
            cliente=self.cliente,
            rede_pai=parent,
            prefixo="2001:db8::/48",
            status="C",
        )
        self.assertEqual(free_subnets(parent, 48, 2), ["2001:db8:1::/48", "2001:db8:2::/48"])

    def test_allocator_is_atomic_and_records_history(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="198.51.100.0/24", status="C")
        user = get_user_model().objects.create_user("noc")
        created = allocate_subnets(
            parent=parent,
            new_prefix=26,
            quantity=2,
            description="Clientes",
            user=user,
        )
        self.assertEqual(
            [item.prefixo for item in created], ["198.51.100.0/26", "198.51.100.64/26"]
        )
        self.assertEqual(self.cliente.historico_ipam.count(), 1)

    def test_next_free_address_skips_child_space(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="192.0.2.0/24", status="A")
        Subrede.objects.create(
            cliente=self.cliente, rede_pai=parent, prefixo="192.0.2.0/28", status="R"
        )
        self.assertEqual(next_free_address(parent), "192.0.2.16")

    def test_free_subnet_skips_direct_address_registered_in_parent(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="192.0.2.0/24")
        EnderecoIP.objects.create(subrede=parent, endereco="192.0.2.10")

        self.assertEqual(free_subnets(parent, 26, 1), ["192.0.2.64/26"])

    def test_child_cannot_cover_address_registered_in_ancestor(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="192.0.2.0/24")
        EnderecoIP.objects.create(subrede=parent, endereco="192.0.2.10")

        with self.assertRaisesMessage(ValidationError, "já está cadastrado"):
            Subrede.objects.create(
                cliente=self.cliente,
                rede_pai=parent,
                prefixo="192.0.2.0/26",
            )

    def test_parent_cannot_be_resized_outside_existing_child(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="198.51.100.0/24")
        Subrede.objects.create(
            cliente=self.cliente,
            rede_pai=parent,
            prefixo="198.51.100.128/25",
        )

        parent.prefixo = "198.51.100.0/25"
        with self.assertRaisesMessage(ValidationError, "fora do bloco pai"):
            parent.save()

    def test_parent_cannot_be_resized_outside_registered_address(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="203.0.113.0/24")
        EnderecoIP.objects.create(subrede=parent, endereco="203.0.113.200")

        parent.prefixo = "203.0.113.0/25"
        with self.assertRaisesMessage(ValidationError, "tornaria o endereço cadastrado"):
            parent.save()

    def test_subnet_with_direct_addresses_cannot_become_container(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="198.18.0.0/24")
        EnderecoIP.objects.create(subrede=subnet, endereco="198.18.0.10")

        subnet.status = "C"
        with self.assertRaisesMessage(ValidationError, "não pode virar contêiner"):
            subnet.save()

    def test_disabled_address_is_not_suggested_for_duplicate_registration(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="192.0.2.0/30")
        EnderecoIP.objects.create(subrede=subnet, endereco="192.0.2.1", status="D")

        self.assertEqual(next_free_address(subnet), "192.0.2.2")

    def test_visual_map_marks_child_space_as_allocated_subnet(self):
        parent = Subrede.objects.create(cliente=self.cliente, prefixo="10.0.0.0/29")
        Subrede.objects.create(
            cliente=self.cliente,
            rede_pai=parent,
            prefixo="10.0.0.4/30",
        )

        cells = {cell["address"]: cell for cell in visual_map(parent)}
        self.assertEqual(cells["10.0.0.4"]["kind"], "subnet")
        self.assertEqual(cells["10.0.0.5"]["label"], "Sub-rede 10.0.0.4/30")

    def test_ipv4_point_to_point_addresses_are_assignable(self):
        subnet = Subrede.objects.create(cliente=self.cliente, prefixo="192.0.2.0/31")
        first = EnderecoIP.objects.create(subrede=subnet, endereco="192.0.2.0")
        second = EnderecoIP.objects.create(subrede=subnet, endereco="192.0.2.1")
        self.assertEqual({first.endereco, second.endereco}, {"192.0.2.0", "192.0.2.1"})


class IPAMAccessTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="Cliente Portal IPAM",
            cnpj="00.000.000/0006-01",
            contato_principal="Cliente",
        )
        self.other = Cliente.objects.create(
            nome_fantasia="Outro Portal IPAM",
            cnpj="00.000.000/0006-02",
            contato_principal="Outro",
        )
        self.subnet = Subrede.objects.create(cliente=self.cliente, prefixo="203.0.113.0/24")
        self.other_subnet = Subrede.objects.create(cliente=self.other, prefixo="198.51.100.0/24")
        self.staff = get_user_model().objects.create_user("staff-ipam", is_staff=True)

    def test_staff_can_open_dedicated_ipam(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("ipam:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gerenciamento de endereços IP")

    def test_customer_cannot_open_operational_ipam(self):
        user = get_user_model().objects.create_user("customer-ipam")
        PerfilCliente.objects.create(usuario=user, cliente=self.cliente)
        self.client.force_login(user)
        response = self.client.get(reverse("ipam:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_customer_reads_only_own_subnet(self):
        user = get_user_model().objects.create_user("portal-ipam")
        PerfilCliente.objects.create(usuario=user, cliente=self.cliente)
        self.client.force_login(user)
        own = self.client.get(reverse("ipam:portal_detail", args=[self.subnet.pk]))
        foreign = self.client.get(reverse("ipam:portal_detail", args=[self.other_subnet.pk]))
        self.assertEqual(own.status_code, 200)
        self.assertContains(own, "Somente consulta")
        self.assertEqual(foreign.status_code, 404)


class IPAMMigrationTests(TransactionTestCase):
    def test_existing_subnets_and_addresses_survive_migration(self):
        migrate_from = [("infraestrutura", "0004_alter_subrede_unique_together_and_more")]
        migrate_to = [("infraestrutura", "0005_historicoipam_secaoipam_vrf_and_more")]

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps
        OldCliente = old_apps.get_model("gestao", "Cliente")
        OldSubrede = old_apps.get_model("infraestrutura", "Subrede")
        OldEnderecoIP = old_apps.get_model("infraestrutura", "EnderecoIP")
        customer = OldCliente.objects.create(
            nome_fantasia="Migração IPAM",
            cnpj="00.000.000/0007-01",
            contato_principal="NOC",
        )
        subnet = OldSubrede.objects.create(cliente=customer, prefixo="198.18.0.0/24")
        address = OldEnderecoIP.objects.create(
            subrede=subnet, endereco="198.18.0.10", descricao="Router"
        )

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps
        NewSubrede = new_apps.get_model("infraestrutura", "Subrede")
        NewEnderecoIP = new_apps.get_model("infraestrutura", "EnderecoIP")
        migrated_subnet = NewSubrede.objects.get(pk=subnet.pk)
        migrated_address = NewEnderecoIP.objects.get(pk=address.pk)

        self.assertEqual(migrated_subnet.prefixo, "198.18.0.0/24")
        self.assertEqual(migrated_subnet.status, "A")
        self.assertIsNone(migrated_subnet.vrf_id)
        self.assertEqual(migrated_address.endereco, "198.18.0.10")
        self.assertEqual(migrated_address.descricao, "Router")
