from django import forms

from accounts.portal_utils import PasswordConfirmForm, StyledForm


class ReasonForm(StyledForm):
    reason = forms.CharField(label="Lý do", max_length=200, required=False)


class SlotConfigForm(PasswordConfirmForm):
    price_per_spray = forms.DecimalField(label="Giá mỗi lần xịt (VND)", min_value=0, max_digits=10, decimal_places=2)
    low_stock_threshold = forms.IntegerField(label="Ngưỡng cảnh báo sắp hết (số lần xịt)", min_value=0)
    spray_duration = forms.IntegerField(label="Thời gian xịt (mili giây)", min_value=100, max_value=5000)
    reason = forms.CharField(label="Ghi chú thay đổi", max_length=200, required=False)

    field_order = ["price_per_spray", "low_stock_threshold", "spray_duration", "reason", "confirm_password"]
