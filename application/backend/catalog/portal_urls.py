from django.urls import path

from . import portal_views as v

urlpatterns = [
    path("", v.catalog_home, name="catalog_home"),
    path("perfumes/new/", v.perfume_edit, name="catalog_perfume_new"),
    path("perfumes/<int:pk>/", v.perfume_edit, name="catalog_perfume_edit"),
    path("locations/new/", v.location_edit, name="catalog_location_new"),
    path("locations/<int:pk>/", v.location_edit, name="catalog_location_edit"),
    path("campaigns/new/", v.campaign_edit, name="catalog_campaign_new"),
    path("campaigns/<int:pk>/", v.campaign_edit, name="catalog_campaign_edit"),
    path("campaigns/<int:pk>/toggle/", v.campaign_toggle, name="catalog_campaign_toggle"),
    path("brand/", v.brand_profile, name="catalog_brand_profile"),
]
