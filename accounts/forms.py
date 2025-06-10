from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Profile
from django.core.exceptions import ValidationError
import random

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    mobile_number = forms.CharField(max_length=15)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.otp = str(random.randint(100000, 999999))
        if commit:
            user.save()
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_pic', 'address', 'linkedin_url', 'twitter_url']

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number']