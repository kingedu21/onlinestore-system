from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User
from products.models import SellerApplication


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'address', 'password1', 'password2')

    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=30)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'phone', 'address')

    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=30)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))


class SellerApplicationForm(forms.ModelForm):
    class Meta:
        model = SellerApplication
        fields = (
            'full_name',
            'business_name',
            'phone_number',
            'email',
            'business_address',
            'mpesa_number',
            'id_number',
            'business_registration',
        )

    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    business_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    business_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    mpesa_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    id_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    business_registration = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
