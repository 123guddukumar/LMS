from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('otp-verification/<int:user_id>/', views.otp_verification, name='otp_verification'),
    path('profile/', views.profile, name='profile'),
    path('contact/', views.contact_view, name='contact'),
    path('certificates/download/<int:course_id>/<int:user_id>/', views.download_certificate, name='download_certificate'),
]