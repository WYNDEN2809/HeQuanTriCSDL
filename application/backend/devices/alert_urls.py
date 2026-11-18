from django.urls import path

from . import alert_views as v

urlpatterns = [
    path("", v.alert_list, name="alert_list"),
    path("<int:pk>/", v.alert_detail, name="alert_detail"),
    path("<int:pk>/action/", v.alert_action, name="alert_action"),
]
