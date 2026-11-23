from django.urls import path

from . import portal_views

urlpatterns = [
    path("", portal_views.ticket_list, name="maintenance_list"),
    path("<int:pk>/", portal_views.ticket_detail, name="maintenance_detail"),
    path("<int:pk>/action/", portal_views.ticket_action, name="maintenance_action"),
]
