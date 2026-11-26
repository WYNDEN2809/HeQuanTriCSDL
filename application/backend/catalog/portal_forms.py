from django import forms

from accounts.portal_utils import StyledForm


class PerfumeForm(StyledForm):
    name = forms.CharField(label="Tên nước hoa", max_length=150, help_text="Lưu không dấu (cột VARCHAR).")
    description = forms.CharField(label="Mô tả / nhóm hương", max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 3}))
    price_per_spray = forms.DecimalField(label="Giá mặc định mỗi lần xịt (VND)", min_value=0, max_digits=10, decimal_places=2)
    is_active = forms.BooleanField(label="Đang kinh doanh", required=False, initial=True)


class LocationForm(StyledForm):
    name = forms.CharField(label="Tên địa điểm", max_length=100)
    address = forms.CharField(label="Địa chỉ", max_length=255, required=False)
    description = forms.CharField(label="Ghi chú", max_length=500, required=False)
    is_active = forms.BooleanField(label="Đang hoạt động", required=False, initial=True)


class BrandProfileForm(StyledForm):
    description = forms.CharField(label="Mô tả thương hiệu", max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 3}))
    logo_url = forms.CharField(label="Địa chỉ logo (https://...)", max_length=255, required=False)


class TenantForm(StyledForm):
    name = forms.CharField(label="Tên thương hiệu", max_length=100)
    description = forms.CharField(label="Mô tả", max_length=500, required=False)
    logo_url = forms.CharField(label="Địa chỉ logo", max_length=255, required=False)


class TenantCreateForm(TenantForm):
    admin_username = forms.CharField(label="Tên đăng nhập Brand Admin đầu tiên", max_length=50)
    admin_email = forms.EmailField(label="Email Brand Admin", max_length=254)
    admin_password = forms.CharField(label="Mật khẩu ban đầu (≥ 8 ký tự)", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))


class CampaignForm(StyledForm):
    """Khuyen mai / dung thu mien phi / gia tam thoi. Danh sach nuoc hoa, dia diem chi gom cua brand dang chon."""

    DT_FORMAT = "%Y-%m-%dT%H:%M"

    name = forms.CharField(label="Tên chương trình", max_length=100, help_text="Lưu không dấu (cột VARCHAR).")
    campaign_type = forms.ChoiceField(label="Loại chương trình", choices=[])
    value = forms.DecimalField(
        label="Giá trị", required=False, min_value=0, max_digits=10, decimal_places=2,
        help_text="Giảm theo %: nhập 1–100. Giá tạm thời: nhập giá mới (VND). Dùng thử miễn phí: bỏ trống.")
    perfume = forms.ModelChoiceField(label="Áp dụng cho nước hoa", queryset=None, required=False, empty_label="Tất cả nước hoa")
    location = forms.ModelChoiceField(label="Áp dụng tại địa điểm", queryset=None, required=False, empty_label="Tất cả địa điểm")
    starts_at = forms.DateTimeField(label="Bắt đầu", input_formats=[DT_FORMAT],
                                    widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT))
    ends_at = forms.DateTimeField(label="Kết thúc", input_formats=[DT_FORMAT],
                                  widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT))
    is_active = forms.BooleanField(label="Đang bật", required=False, initial=True)

    def __init__(self, *args, brand_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Campaign, Location, Perfume

        self.fields["campaign_type"].choices = Campaign.Type.choices
        self.fields["perfume"].queryset = Perfume.objects.filter(brand_id=brand_id).order_by("name")
        self.fields["location"].queryset = Location.objects.filter(brand_id=brand_id).order_by("name")
