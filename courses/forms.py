from django import forms
from .models import Course, CourseModule, Lesson

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'category', 'price', 'discount_price', 
                 'thumbnail', 'duration', 'is_free', 'instructor']

class ModuleForm(forms.ModelForm):
    class Meta:
        model = CourseModule
        fields = ['title', 'description', 'order']

class LessonForm(forms.ModelForm):
    video_file = forms.FileField(required=True, label="Upload Video File")

    class Meta:
        model = Lesson
        fields = ['title', 'duration', 'order', 'module']

    def clean(self):
        cleaned_data = super().clean()
        video_file = cleaned_data.get('video_file')

        if video_file:
            if not video_file.name.lower().endswith(('.mp4', '.mov', '.avi')):
                raise forms.ValidationError("Only MP4, MOV, or AVI files are allowed.")
            if video_file.size > 100 * 1024 * 1024:
                raise forms.ValidationError("Video file size must be under 100MB.")

        return cleaned_data

class AdminLessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'duration', 'order', 'module', 'video_url', 'cloudinary_public_id']