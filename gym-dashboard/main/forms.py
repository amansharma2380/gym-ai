from django import forms
from django.contrib.auth.models import User
from .models import MemberProfile, ProgressEntry, Payment

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Repeat password")

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError("Passwords don't match.")
        return cd.get('password2')

class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ['phone','age','height_cm','weight_kg','gender','goal','experience_level']

class ProgressEntryForm(forms.ModelForm):
    class Meta:
        model = ProgressEntry
        fields = ['date','weight_kg','body_fat_pct','notes']

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount']
