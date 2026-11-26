from importlib import import_module

from django.contrib import admin
from django.urls import include, path


def optional_include(prefix, module):
    """
    Chi them URL cua mot module portal neu file do da ton tai.
    Nho vay moi nguoi lam tren nhanh rieng van chay duoc du chua co phan cua nguoi khac.
    (Loi thieu module KHAC ben trong van duoc bao nhu binh thuong.)
    """
    try:
        import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name != module:
            raise
        return []
    return [path(prefix, include(module))]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("reports.urls")),
    path("", include("sales.urls")),      # webhook thanh toan + trang thanh toan gia lap
    path("", include("devices.urls")),    # API cho thiet bi kiosk
    path("kiosk/", include("kiosk.urls")),
]

# Portal van hanh (Buoc 3-5). Moi dong: tien to URL, module url (ghi chu: nguoi phu trach).
PORTAL_ROUTES = [
    ("portal/transactions/", "sales.portal_urls"),         # Nguoi 4
    ("portal/alerts/", "devices.alert_urls"),              # Nguoi 3
    ("portal/machines/", "devices.machine_urls"),          # Nguoi 2
    ("portal/maintenance/", "maintenance.portal_urls"),    # Nguoi 5
    ("portal/inventory/", "inventory.portal_urls"),        # Nguoi 2
    ("portal/people/", "accounts.portal_urls"),            # Nguoi 1
    ("portal/catalog/", "catalog.portal_urls"),            # Nguoi 1
    ("portal/tenants/", "catalog.tenant_urls"),            # Nguoi 1
    ("portal/reports/", "reports.portal_urls"),            # Nguoi 3
    ("portal/audit/", "reports.audit_urls"),               # Nguoi 1
]
for _prefix, _module in PORTAL_ROUTES:
    urlpatterns += optional_include(_prefix, _module)
