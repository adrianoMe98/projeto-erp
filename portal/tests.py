import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from gestao.models import Cliente
from infraestrutura.models import Subrede
from portal.models import PerfilCliente


class UnifiedLoginTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="Cliente Portal",
            cnpj="00.000.000/0003-01",
            contato_principal="Responsável",
        )
        self.user = get_user_model().objects.create_user(
            "portal-user", email="portal@example.com", password="senha-forte-123"
        )
        PerfilCliente.objects.create(usuario=self.user, cliente=self.cliente)

    def test_login_by_username_redirects_customer_to_portal(self):
        response = self.client.post(
            reverse("login"), {"username": "portal-user", "password": "senha-forte-123"}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_by_email_redirects_staff_to_admin(self):
        staff = get_user_model().objects.create_user(
            "operador",
            email="operador@example.com",
            password="senha-forte-123",
            is_staff=True,
        )
        response = self.client.post(
            reverse("login"),
            {"username": staff.email, "password": "senha-forte-123"},
        )
        self.assertRedirects(response, reverse("admin:index"), fetch_redirect_response=False)

    def test_customer_cannot_use_next_to_enter_admin(self):
        response = self.client.post(
            f"{reverse('login')}?next=/admin/",
            {"username": self.user.username, "password": "senha-forte-123", "next": "/admin/"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_user_without_profile_gets_explanatory_page(self):
        user = get_user_model().objects.create_user("sem-vinculo", password="senha-forte-123")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("sem_acesso"), fetch_redirect_response=False)

    def test_ambiguous_duplicate_email_does_not_authenticate(self):
        get_user_model().objects.create_user(
            "duplicado", email=self.user.email, password="senha-forte-123"
        )
        response = self.client.post(
            reverse("login"), {"username": self.user.email, "password": "senha-forte-123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inválidos")

    def test_admin_login_redirects_to_central_page(self):
        response = self.client.get("/admin/login/?next=/admin/")
        self.assertRedirects(response, "/login/?next=%2Fadmin%2F")

    def test_login_includes_theme_switcher(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, static("js/theme.js"))


class ProductionAdminSmokeTests(TestCase):
    def test_admin_index_renders_with_manifest_static_storage(self):
        user = get_user_model().objects.create_superuser(
            "admin-smoke", "admin-smoke@example.com", "senha-forte-123"
        )
        self.client.force_login(user)

        with (
            tempfile.TemporaryDirectory() as static_root,
            override_settings(
                DEBUG=False,
                STATIC_ROOT=static_root,
                STORAGES={
                    "default": {
                        "BACKEND": "django.core.files.storage.FileSystemStorage",
                    },
                    "staticfiles": {
                        "BACKEND": "core.storage.JazzminCompatibleStaticFilesStorage",
                    },
                },
            ),
        ):
            call_command("collectstatic", interactive=False, verbosity=0)
            response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Painel de Controle")
        self.assertContains(response, "admin_theme")


class RuntimeHealthTests(TestCase):
    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^health/$"])
    def test_internal_healthcheck_is_not_redirected_to_https(self):
        response = self.client.get(reverse("healthcheck"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], settings.ERP_VERSION)


class PortalTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome_fantasia="Cliente Portal 2",
            cnpj="00.000.000/0003-02",
            contato_principal="Responsável",
        )
        self.user = get_user_model().objects.create_user("cliente-2", password="senha-forte-123")
        PerfilCliente.objects.create(usuario=self.user, cliente=self.cliente)
        self.client.force_login(self.user)

    def test_dashboard_renders_subnets_at_any_level(self):
        root = Subrede.objects.create(cliente=self.cliente, prefixo="10.10.0.0/16")
        child = Subrede.objects.create(cliente=self.cliente, rede_pai=root, prefixo="10.10.1.0/24")
        Subrede.objects.create(cliente=self.cliente, rede_pai=child, prefixo="10.10.1.0/28")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10.10.1.0/24")
        self.assertContains(response, "10.10.1.0/28")

    def test_new_ticket_validates_and_saves_customer(self):
        invalid = self.client.post(reverse("novo_ticket"), {"titulo": "Oi", "descricao": "curta"})
        self.assertEqual(invalid.status_code, 200)
        valid = self.client.post(
            reverse("novo_ticket"),
            {
                "titulo": "Falha na autenticação",
                "descricao": "O serviço apresenta erro desde ontem.",
            },
        )
        self.assertRedirects(valid, reverse("dashboard"))
        self.assertEqual(self.cliente.tickets.count(), 1)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_portal_includes_theme_switcher_and_runtime_version(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, f"v{settings.ERP_VERSION}")
