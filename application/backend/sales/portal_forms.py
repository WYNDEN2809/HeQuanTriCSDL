from django import forms

from accounts.portal_utils import PasswordConfirmForm, StyledForm


class ActionForm(PasswordConfirmForm):
    reason = forms.CharField(label="Lý do / ghi chú", max_length=300)
    field_order = ["reason", "confirm_password"]


class ReconcileForm(StyledForm):
    file = forms.FileField(label="File CSV của nhà cung cấp (cột: provider_transaction_id, amount, status, payment_reference)")
    d_from = forms.DateField(label="Từ ngày", widget=forms.DateInput(attrs={"type": "date"}))
    d_to = forms.DateField(label="Đến ngày", widget=forms.DateInput(attrs={"type": "date"}))
