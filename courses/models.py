# courses/models.py
from django.db import models
from accounts.models import User
from django.utils.text import slugify
import cloudinary
from cloudinary.models import CloudinaryField
import logging
import time
import cloudinary.utils

logger = logging.getLogger(__name__)

class CourseCategory(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails')
    duration = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_free = models.BooleanField(default=False)
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'is_staff': True})
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey('CourseModule', on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    video_url = models.URLField(blank=True, null=True)
    cloudinary_public_id = models.CharField(max_length=200, blank=True, null=True)
    duration = models.DurationField()
    order = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"

    def get_secure_streaming_url(self, expires_in=3600):
        """Generate a secure, time-limited streaming URL."""
        if self.cloudinary_public_id:
            try:
                # Check if signed URLs are required (based on your Cloudinary settings)
                # If "Restrict access to signed URLs" is enabled in Cloudinary Security settings,
                # set sign_url=True. Otherwise, sign_url=False.
                sign_url = False  # Adjust this based on your Cloudinary settings
                url = cloudinary.utils.cloudinary_url(
                    self.cloudinary_public_id,
                    resource_type="video",
                    secure=True,
                    sign_url=sign_url,
                    expires_at=int(time.time()) + expires_in if sign_url else None
                )[0]
                logger.info(f"Generated Cloudinary URL for lesson {self.id}: {url}")
                return url
            except Exception as e:
                logger.error(f"Failed to generate Cloudinary URL for lesson {self.id}: {str(e)}")
                return None
        logger.warning(f"No video source available for lesson {self.id}")
        return None

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    progress_percentage = models.FloatField(default=0.0)
    last_watched = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True) 

    class Meta:
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} - {self.progress_percentage}%"

class LessonBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.lesson.title}"

class LessonViewAnalytics(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"View of {self.lesson.title} by {self.user.username if self.user else 'Anonymous'}"

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    enrollment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"