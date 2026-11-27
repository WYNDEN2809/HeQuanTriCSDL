from django.urls import path

from . import portal_views as v
from . import report_views as r

urlpatterns = [
    path("", v.ticket_list, name="mt_list"),
    path("new/", v.ticket_create, name="mt_create"),
    path("report/", r.maintenance_report, name="mt_report"),
    path("<int:pk>/", v.ticket_detail, name="mt_detail"),
    path("<int:pk>/action/", v.ticket_action, name="mt_action"),
]
