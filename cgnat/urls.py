from django.urls import path

from cgnat import views

app_name = "cgnat"
urlpatterns = [
    path("relatorios/<uuid:generation_id>/", views.report_download, name="report"),
    path("scripts/<uuid:generation_id>/", views.script_download, name="script"),
]
