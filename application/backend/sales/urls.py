from django.urls import path

from . import views

urlpatterns = [
    path("api/payments/webhook/", views.payment_webhook, name="payment_webhook"),
    path("pay/<str:reference>/", views.pay_sandbox, name="pay_sandbox"),
]
