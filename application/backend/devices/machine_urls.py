from django.urls import path

from . import machine_views as v

urlpatterns = [
    path("", v.machine_list, name="machine_list"),
    path("<int:pk>/", v.machine_detail, name="machine_detail"),
    path("<int:pk>/action/", v.machine_action, name="machine_action"),
    path("slots/<int:slot_pk>/action/", v.slot_action, name="machine_slot_action"),
    path("slots/<int:slot_pk>/config/", v.slot_config, name="machine_slot_config"),
]
