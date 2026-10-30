from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from cgnat.models import CgnatGeneration, CgnatPlan
from cgnat.services.generators import create_generation


@admin.register(CgnatPlan)
class CgnatPlanAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "cliente",
        "rede_privada",
        "rede_publica",
        "portas_por_assinante",
        "ativo",
    )
    list_filter = ("ativo", "cliente")
    search_fields = ("nome", "cliente__nome_fantasia", "rede_privada", "rede_publica")
    actions = (
        "generate_all_targets",
        "generate_routeros6",
        "generate_routeros7",
        "generate_iptables",
        "generate_nftables",
    )

    @admin.action(description="Gerar configurações para todas as plataformas")
    def generate_all_targets(self, request, queryset):
        for target, _label in CgnatGeneration.Target.choices:
            self._generate(request, queryset, target)

    def _generate(self, request, queryset, target):
        generated = 0
        for plan in queryset:
            try:
                create_generation(plan, target, request.user)
                generated += 1
            except Exception as exc:
                self.message_user(request, f"{plan}: {exc}", level=messages.ERROR)
        if generated:
            target_label = dict(CgnatGeneration.Target.choices)[target]
            self.message_user(
                request,
                f"{generated} configuração(ões) {target_label} gerada(s).",
                level=messages.SUCCESS,
            )

    @admin.action(description="Gerar configuração MikroTik RouterOS 6")
    def generate_routeros6(self, request, queryset):
        self._generate(request, queryset, CgnatGeneration.Target.ROUTEROS6)

    @admin.action(description="Gerar configuração MikroTik RouterOS 7")
    def generate_routeros7(self, request, queryset):
        self._generate(request, queryset, CgnatGeneration.Target.ROUTEROS7)

    @admin.action(description="Gerar configuração Linux iptables")
    def generate_iptables(self, request, queryset):
        self._generate(request, queryset, CgnatGeneration.Target.IPTABLES)

    @admin.action(description="Gerar configuração Linux nftables")
    def generate_nftables(self, request, queryset):
        self._generate(request, queryset, CgnatGeneration.Target.NFTABLES)


@admin.register(CgnatGeneration)
class CgnatGenerationAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "target",
        "created_at",
        "created_by",
        "disponivel_cliente",
        "downloads",
    )
    list_filter = ("target", "disponivel_cliente", "plan__cliente")
    search_fields = ("plan__nome", "plan__cliente__nome_fantasia", "sha256")
    readonly_fields = (
        "plan",
        "target",
        "content",
        "sha256",
        "mapping_snapshot",
        "summary",
        "created_by",
        "created_at",
    )

    @admin.display(description="Arquivos")
    def downloads(self, obj):
        return format_html(
            '<a href="{}">Relatório PDF</a> | <a href="{}">Script</a>',
            reverse("cgnat:report", args=[obj.pk]),
            reverse("cgnat:script", args=[obj.pk]),
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
