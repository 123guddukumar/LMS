from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('otp_verification/<int:user_id>/', views.otp_verification, name='otp_verification'),
    path('profile/', views.profile, name='profile'),
    path('certificates/download/<int:course_id>/<int:user_id>/', views.download_certificate, name='download_certificate'),
]