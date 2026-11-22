from django import forms

from accounts.models import BrandMember
from accounts.portal_utils import PasswordConfirmForm, StyledForm
from devices.models import Machine

from .models import MaintenanceRecord

PRIORITY_CHOICES = [("LOW", "Thấp"), ("MEDIUM", "Trung bình"), ("HIGH", "Cao"), ("CRITICAL", "Nghiêm trọng (khóa máy)")]


def technician_choices(brand_ids=None, brand_id=None):
    qs = BrandMember.objects.filter(brand_role="TECHNICIAN", user__is_active=True).select_related("user")
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    elif brand_ids is not None:
        qs = qs.filter(brand_id__in=brand_ids)
    return [(m.user_id, m.user.username) for m in qs.order_by("user__username")]


class TicketForm(StyledForm):
    machine = forms.ChoiceField(label="Máy")
    maintenance_type = forms.ChoiceField(label="Loại bảo trì", choices=MaintenanceRecord.Type.choices)
    priority = forms.ChoiceField(label="Mức ưu tiên", choices=PRIORITY_CHOICES, initial="MEDIUM")
    assigned_to = forms.ChoiceField(label="Giao cho kỹ thuật viên", required=False)
    description = forms.CharField(label="Mô tả", max_length=400, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, machines=None, **kwargs):
        super().__init__(*args, **kwargs)
        machines = list(machines if machines is not None else Machine.objects.none())
        self.fields["machine"].choices = [(m.pk, f"{m.name} ({m.serial_number})") for m in machines]
        brand_ids = {m.brand_id for m in machines}
        self.fields["assigned_to"].choices = [("", "(chưa giao)")] + technician_choices(brand_ids=brand_ids)


class SimpleNoteForm(StyledForm):
    note = forms.CharField(required=False, max_length=500)
    priority = forms.ChoiceField(required=False, choices=PRIORITY_CHOICES)
    technician = forms.IntegerField(required=False)
    item_id = forms.IntegerField(required=False)
    done = forms.BooleanField(required=False)
    text = forms.CharField(required=False, max_length=500)
    slot = forms.IntegerField(required=False)
    purpose = forms.ChoiceField(required=False, choices=[("diag", "Xịt thử chẩn đoán"), ("post", "Xịt thử sau bảo trì")])
    passed = forms.BooleanField(required=False)


class SprayConfirmForm(PasswordConfirmForm):
    """Xit thu la thao tac nhay cam: can nhap lai mat khau."""
