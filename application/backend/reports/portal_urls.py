from django.urls import path

from . import portal_views as v

urlpatterns = [
    path("", v.dashboard, name="report_dashboard"),
    path("export/<str:kind>/", v.export, name="report_export"),
]
