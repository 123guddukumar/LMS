from django.contrib import admin
from .models import CourseCategory, Course, CourseModule, Lesson, Enrollment, LessonProgress, LessonBookmark, LessonViewAnalytics
from .forms import AdminLessonForm  # Use the admin-specific form

# Inline for CourseModule to display under Course
class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1
    ordering = ['order']
    fields = ['title', 'description', 'order']

# Inline for Lesson to display under CourseModule
class LessonInline(admin.TabularInline):
    model = Lesson
    form = AdminLessonForm  # Use AdminLessonForm to avoid video_file error
    extra = 1
    ordering = ['order']
    fields = ['title', 'duration', 'order', 'video_url', 'cloudinary_public_id']  # Remove 'video_file'
    readonly_fields = ['cloudinary_public_id', 'video_url']  # Prevent editing Cloudinary fields directly

@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'instructor', 'price', 'is_free', 'created_at']
    list_filter = ['category', 'is_free', 'instructor']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CourseModuleInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'category', 'instructor')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'is_free')
        }),
        ('Details', {
            'fields': ('thumbnail', 'duration', 'created_at', 'updated_at')
        }),
    )

@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    search_fields = ['title', 'description']
    inlines = [LessonInline]
    ordering = ['course', 'order']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = AdminLessonForm  # Use AdminLessonForm to avoid video_file error
    list_display = ['title', 'module', 'order', 'duration', 'video_url']
    list_filter = ['module__course']
    search_fields = ['title', 'module__title']
    readonly_fields = ['cloudinary_public_id', 'video_url']
    ordering = ['module', 'order']
    fieldsets = (
        (None, {
            'fields': ('title', 'module', 'order', 'duration')
        }),
        ('Video', {
            'fields': ('video_url', 'cloudinary_public_id')
        }),
    )

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'amount', 'enrolled_at', 'is_active']
    list_filter = ['course', 'is_active']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['enrolled_at', 'payment_id']
    ordering = ['-enrolled_at']

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'progress_percentage', 'last_watched']
    list_filter = ['lesson__module__course']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['last_watched']
    ordering = ['-last_watched']

@admin.register(LessonBookmark)
class LessonBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'created_at']
    list_filter = ['lesson__module__course']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

@admin.register(LessonViewAnalytics)
class LessonViewAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'user', 'viewed_at']
    list_filter = ['lesson__module__course']
    search_fields = ['lesson__title', 'user__username']
    readonly_fields = ['viewed_at']
    ordering = ['-viewed_at']