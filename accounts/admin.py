# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, UserActivity, Certificate
from .forms import UserRegisterForm
from django import forms
from django.core.exceptions import ValidationError

class CustomUserAdmin(UserAdmin):
    add_form = UserRegisterForm
    model = User
    list_display = ('username', 'email', 'mobile_number', 'is_verified', 'is_staff', 'last_login')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'last_login')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'mobile_number')}),
        ('Permissions', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_number', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'mobile_number')
    ordering = ('-date_joined',)
    actions = ['mark_verified', 'mark_unverified']

    def mark_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_verified.short_description = "Mark selected users as verified"

    def mark_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    mark_unverified.short_description = "Mark selected users as unverified"

admin.site.register(User, CustomUserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile_number', 'short_address', 'profile_pic_display')
    search_fields = ('user__username', 'user__email', 'address')
    list_filter = ('user__is_verified',)

    def mobile_number(self, obj):
        return obj.user.mobile_number
    mobile_number.short_description = 'Mobile Number'

    def short_address(self, obj):
        return obj.address[:50] + '...' if obj.address and len(obj.address) > 50 else obj.address
    short_address.short_description = 'Address'

    def profile_pic_display(self, obj):
        return obj.profile_pic.url if obj.profile_pic else 'No Image'
    profile_pic_display.short_description = 'Profile Picture'

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('timestamp',)

class CertificateAdminForm(forms.ModelForm):
    certificate_file = forms.FileField(
        required=False,
        help_text="Upload a certificate file (PDF). If provided, it will override the URL.",
        validators=[
            lambda f: f.name.lower().endswith('.pdf') or ValidationError("Only PDF files are allowed.")
        ]
    )

    class Meta:
        model = Certificate
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)
        uploaded_file = self.cleaned_data.get('certificate_file')

        if commit:
            instance.save()
            if uploaded_file:
                instance.certificate_file = uploaded_file
                instance.save()
                instance.certificate_url = instance.certificate_file.url
            instance.save()
        return instance

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    form = CertificateAdminForm
    list_display = ('user', 'course', 'date_issued', 'issued_by', 'certificate_url')
    search_fields = ('user__username', 'course__title')
    list_filter = ('date_issued', 'issued_by')
    date_hierarchy = 'date_issued'

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new certificate
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)