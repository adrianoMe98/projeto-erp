from django.contrib import admin
from django.urls import include, path

from core.views import healthcheck
from portal.views import UnifiedLoginView, admin_login_redirect

urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("login/", UnifiedLoginView.as_view(), name="login"),
    path("admin/login/", admin_login_redirect, name="admin_login_redirect"),
    path("admin/", admin.site.urls),
    path("ipam/", include("infraestrutura.urls")),
    path("cgnat/", include("cgnat.urls")),
    path("pagamentos/", include("pagamentos.urls")),
    path("", include("portal.urls")),
]
