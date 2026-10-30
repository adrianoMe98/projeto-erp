from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from pagamentos.models import PixCharge, PixWebhookEvent
from pagamentos.services.simulator import simulate_payment


@admin.register(PixCharge)
class PixChargeAdmin(admin.ModelAdmin):
    list_display = ("txid", "cliente", "valor", "status", "expires_at", "created_at", "portal_link")
    list_filter = ("status", "cliente", "provider")
    search_fields = ("txid", "cliente__nome_fantasia", "descricao")
    readonly_fields = (
        "txid",
        "provider",
        "provider_charge_id",
        "pix_copy_paste",
        "paid_at",
        "created_at",
        "updated_at",
    )
    actions = ("mark_as_paid_in_simulator",)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not settings.PIX_ENABLED:
            actions.pop("mark_as_paid_in_simulator", None)
        return actions

    def has_add_permission(self, request):
        return settings.PIX_ENABLED and super().has_add_permission(request)

    @admin.action(description="Simular confirmação de pagamento")
    def mark_as_paid_in_simulator(self, request, queryset):
        processed = 0
        for charge in queryset.exclude(status=PixCharge.Status.PAID):
            simulate_payment(charge)
            processed += 1
        self.message_user(
            request,
            f"{processed} cobrança(s) confirmada(s) pelo simulador.",
            level=messages.SUCCESS,
        )

    @admin.display(description="Portal")
    def portal_link(self, obj):
        if not settings.PIX_ENABLED:
            return "Pix desabilitado"
        return format_html(
            '<a href="{}">Visualizar</a>', reverse("pagamentos:detail", args=[obj.pk])
        )


@admin.register(PixWebhookEvent)
class PixWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "charge", "processed_at")
    search_fields = ("event_id", "charge__txid")
    readonly_fields = ("event_id", "event_type", "charge", "payload", "processed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
