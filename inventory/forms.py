from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Asset, CellphoneSpec, LaptopSpec, MonitorSpec, OtherSpec

User = get_user_model()


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
        required=True,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}),
        required=True,
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            # Check if user exists in the database
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None

            # If user exists and password is correct, check if disabled
            if user and user.check_password(password):
                if not user.is_active:
                    raise ValidationError(
                        "Your account has been disabled. Please contact an Administrator.",
                        code="disabled_account",
                    )

        return super().clean()


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "unit_name",
            "company_tag",
            "serial_number",
            "asset_type",
            "assigned_to",
            "status",
            "date_purchased",
        ]
        widgets = {
            "unit_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_tag": forms.TextInput(attrs={"class": "form-control"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control"}),
            "asset_type": forms.Select(attrs={"class": "form-select", "id": "asset_type"}),
            "assigned_to": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "date_purchased": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


# Spec Forms
class LaptopSpecForm(forms.ModelForm):
    class Meta:
        model = LaptopSpec
        fields = ["brand", "model", "ram", "cpu", "gpu"]
        widgets = {f: forms.TextInput(attrs={"class": "form-control"}) for f in fields}


class MonitorSpecForm(forms.ModelForm):
    class Meta:
        model = MonitorSpec
        fields = ["brand", "model"]
        widgets = {f: forms.TextInput(attrs={"class": "form-control"}) for f in fields}


class CellphoneSpecForm(forms.ModelForm):
    class Meta:
        model = CellphoneSpec
        fields = ["brand", "model"]
        widgets = {f: forms.TextInput(attrs={"class": "form-control"}) for f in fields}


class OtherSpecForm(forms.ModelForm):
    class Meta:
        model = OtherSpec
        fields = ["brand"]
        widgets = {"brand": forms.TextInput(attrs={"class": "form-control"})}
