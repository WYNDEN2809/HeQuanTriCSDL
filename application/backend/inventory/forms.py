from django import forms

from accounts.portal_utils import StyledForm
from catalog.models import Perfume


class RefillForm(StyledForm):
    new_quantity = forms.IntegerField(label="Số lần xịt sau khi nạp", min_value=1)
    reason = forms.CharField(label="Lý do (tối đa 30 ký tự)", max_length=30)


class ReplaceForm(StyledForm):
    perfume = forms.ChoiceField(label="Mùi hương của chai mới")
    new_quantity = forms.IntegerField(label="Số lần xịt của chai mới", min_value=1)
    reason = forms.CharField(label="Lý do (tối đa 30 ký tự)", max_length=30)

    def __init__(self, *args, brand_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        perfumes = Perfume.objects.filter(brand_id=brand_id, is_active=True).order_by("name")
        self.fields["perfume"].choices = [(p.id, p.name) for p in perfumes]

    def clean_perfume(self):
        return int(self.cleaned_data["perfume"])


class AdjustForm(StyledForm):
    measured_quantity = forms.IntegerField(label="Số lần xịt đo được (cảm biến/cân)", min_value=0)
    reason = forms.CharField(label="Lý do (tối đa 30 ký tự)", max_length=30)
