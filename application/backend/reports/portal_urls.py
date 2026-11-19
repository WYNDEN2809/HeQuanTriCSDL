from django.urls import path

from . import notification_views, portal_views as v

urlpatterns = [
    path("", v.dashboard, name="report_dashboard"),
    path("export/<str:kind>/", v.export, name="report_export"),
    path("notifications/", notification_views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", notification_views.notification_read, name="notification_read"),
]
