from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("reports.urls")),
    path("", include("sales.urls")),      # webhook thanh toan + trang thanh toan gia lap
    path("", include("devices.urls")),    # API cho thiet bi kiosk
    path("kiosk/", include("kiosk.urls")),
]
