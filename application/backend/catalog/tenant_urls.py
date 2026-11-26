from django.urls import path

from . import tenant_views as v

urlpatterns = [
    path("", v.tenant_list, name="tenant_list"),
    path("new/", v.tenant_create, name="tenant_create"),
    path("<int:pk>/", v.tenant_detail, name="tenant_detail"),
    path("<int:pk>/action/", v.tenant_action, name="tenant_action"),
]
