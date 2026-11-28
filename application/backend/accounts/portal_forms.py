from django import forms

from .models import BrandMember
from .portal_utils import StyledForm


class MemberCreateForm(StyledForm):
    username = forms.CharField(label="Tên đăng nhập", max_length=50)
    email = forms.EmailField(label="Email", max_length=254)
    password = forms.CharField(label="Mật khẩu ban đầu (≥ 8 ký tự)", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    brand_role = forms.ChoiceField(label="Vai trò", choices=BrandMember.BrandRole.choices)


class MemberActionForm(StyledForm):
    brand_role = forms.ChoiceField(required=False, choices=BrandMember.BrandRole.choices)
    new_password = forms.CharField(required=False, max_length=100)
