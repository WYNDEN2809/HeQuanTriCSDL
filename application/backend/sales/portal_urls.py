from django.urls import path

from . import portal_views as v

urlpatterns = [
    path("", v.tx_list, name="tx_list"),
    path("<int:pk>/", v.tx_detail, name="tx_detail"),
    path("<int:pk>/action/", v.tx_action, name="tx_action"),
    path("reconcile/", v.reconcile_view, name="tx_reconcile"),
    path("reconcile/export/", v.reconcile_export, name="tx_reconcile_export"),
]
