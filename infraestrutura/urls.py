from django.urls import path

from . import views

app_name = "ipam"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("redes/nova/", views.subnet_create, name="subnet_create"),
    path("redes/<int:subnet_id>/", views.subnet_detail, name="subnet_detail"),
    path("redes/<int:subnet_id>/editar/", views.subnet_edit, name="subnet_edit"),
    path("redes/<int:subnet_id>/subdividir/", views.subnet_split, name="subnet_split"),
    path("redes/<int:subnet_id>/enderecos/novo/", views.address_create, name="address_create"),
    path(
        "redes/<int:subnet_id>/enderecos/<int:address_id>/editar/",
        views.address_edit,
        name="address_edit",
    ),
    path("cliente/redes/<int:subnet_id>/", views.portal_subnet_detail, name="portal_detail"),
]
