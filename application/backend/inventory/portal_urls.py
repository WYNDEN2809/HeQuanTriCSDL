from django.urls import path

from . import portal_views

urlpatterns = [
    path("", portal_views.report, name="inv_report"),
    path("refill/<int:pk>/", portal_views.refill, name="inv_refill"),
]
