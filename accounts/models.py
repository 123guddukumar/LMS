# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, URLValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    mobile_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', 
                                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    mobile_number = models.CharField(validators=[mobile_regex], max_length=17, blank=True)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics', default='default_profile.png')
    address = models.TextField(max_length=300, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True, validators=[URLValidator()])
    twitter_url = models.URLField(blank=True, null=True, validators=[URLValidator()])

    def __str__(self):
        return f'{self.user.username} Profile'

    def get_profile_completion(self):
        fields = [
            self.profile_pic.name != 'default_profile.png',
            bool(self.address),
            bool(self.user.mobile_number),
            bool(self.linkedin_url),
            bool(self.twitter_url)
        ]
        completed = sum(1 for field in fields if field)
        return (completed / len(fields)) * 100

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"

class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='certificates')
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)  # New field to store the file
    certificate_url = models.URLField(blank=True, null=True)
    date_issued = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_certificates', limit_choices_to={'is_staff': True})

    def __str__(self):
        return f"Certificate for {self.user.username} - {self.course.title}"

    def get_certificate_url(self):
        # Return the URL of the uploaded file if available, otherwise return the manual URL
        if self.certificate_file:
            return self.certificate_file.url
        return self.certificate_url