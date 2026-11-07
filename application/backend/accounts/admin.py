from django.contrib import admin

from .models import BrandMember, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email")
    exclude = ("password",)

    def has_add_permission(self, request):
        return False  # tao tai khoan bang lenh createsuperuser / form quan ly user sau nay

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BrandMember)
class BrandMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "brand", "brand_role")
    list_filter = ("brand", "brand_role")
    search_fields = ("user__username",)
