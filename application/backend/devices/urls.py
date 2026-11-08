from django.urls import path

from . import api

urlpatterns = [
    path("api/device/<str:serial>/heartbeat/", api.heartbeat, name="device_heartbeat"),
    path("api/device/<str:serial>/commands/", api.commands, name="device_commands"),
    path("api/device/<str:serial>/commands/<str:command_id>/ack/", api.ack, name="device_ack"),
    path("api/device/<str:serial>/commands/<str:command_id>/result/", api.result, name="device_result"),
]
