from django.urls import path

<<<<<<< HEAD
from . import portal_views

urlpatterns = [
    path("", portal_views.ticket_list, name="maintenance_list"),
    path("<int:pk>/", portal_views.ticket_detail, name="maintenance_detail"),
    path("<int:pk>/action/", portal_views.ticket_action, name="maintenance_action"),
=======
from . import portal_views as v
from . import report_views as r

urlpatterns = [
    path("", v.ticket_list, name="mt_list"),
    path("new/", v.ticket_create, name="mt_create"),
    path("report/", r.maintenance_report, name="mt_report"),
    path("<int:pk>/", v.ticket_detail, name="mt_detail"),
    path("<int:pk>/action/", v.ticket_action, name="mt_action"),
>>>>>>> origin/main
]
