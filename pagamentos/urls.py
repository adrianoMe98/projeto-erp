from django.urls import path

from pagamentos import views

app_name = "pagamentos"
urlpatterns = [
    path("pix/<uuid:charge_id>/", views.charge_detail, name="detail"),
    path("pix/<uuid:charge_id>/qr.svg", views.charge_qr, name="qr"),
    path("pix/webhooks/simulador/", views.simulator_webhook, name="simulator_webhook"),
]
