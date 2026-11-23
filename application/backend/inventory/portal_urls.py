from django.urls import path

from . import portal_views as v

urlpatterns = [
    path("", v.slot_overview, name="inv_slots"),
    path("slots/<int:slot_pk>/refill/", v.refill, name="inv_refill"),
    path("slots/<int:slot_pk>/replace/", v.replace, name="inv_replace"),
    path("slots/<int:slot_pk>/adjust/", v.adjust, name="inv_adjust"),
    path("movements/", v.movements, name="inv_movements"),
    path("report/", v.report, name="inv_report"),
]
