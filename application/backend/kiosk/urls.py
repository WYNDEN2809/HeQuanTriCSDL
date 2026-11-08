from django.urls import path

from . import views

urlpatterns = [
    path("", views.machines, name="kiosk_machines"),
    path("m/<int:machine_id>/", views.machine_home, name="kiosk_machine"),
    path("m/<int:machine_id>/order/", views.create_order_view, name="kiosk_create_order"),
    path("order/<str:reference>/", views.order_page, name="kiosk_order"),
    path("order/<str:reference>/status/", views.order_status, name="kiosk_order_status"),
    path("order/<str:reference>/cancel/", views.cancel_order_view, name="kiosk_cancel_order"),
]
