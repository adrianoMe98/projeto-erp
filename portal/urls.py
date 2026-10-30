from django.contrib.auth import views as auth_views
from django.urls import path

from portal import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("acesso-pendente/", views.sem_acesso, name="sem_acesso"),
    path("novo-chamado/", views.novo_ticket, name="novo_ticket"),
    path(
        "contratos/<int:contrato_id>/download/",
        views.contrato_download,
        name="contrato_download",
    ),
    path(
        "senha/recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="portal/registration/password_reset_form.html",
            email_template_name="portal/registration/password_reset_email.txt",
            success_url="/senha/recuperar/enviado/",
        ),
        name="password_reset",
    ),
    path(
        "senha/recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="portal/registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "senha/redefinir/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="portal/registration/password_reset_confirm.html",
            success_url="/senha/redefinir/concluido/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "senha/redefinir/concluido/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="portal/registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
