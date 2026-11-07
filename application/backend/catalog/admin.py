from django.contrib import admin

from .models import Brand, Location, Perfume


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand", "address", "is_active")
    list_filter = ("brand", "is_active")
    search_fields = ("name", "address")


@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand", "price_per_spray", "is_active")
    list_filter = ("brand", "is_active")
    search_fields = ("name",)
