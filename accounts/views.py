from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserRegisterForm, ProfileUpdateForm, UserUpdateForm
from .models import User, Profile, UserActivity, Certificate, ContactMessage
from django.contrib.auth.decorators import login_required
from courses.models import Course, Lesson, LessonProgress, Enrollment
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from io import BytesIO
import random
import string


def generate_otp(length=6):
    """Generate a random OTP of specified length."""
    characters = string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send OTP via email
            subject = 'Verify Your Email'
            message = f'Your OTP is: {user.otp}'
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email,]
            send_mail(subject, message, email_from, recipient_list)
            
            messages.success(request, f'Account created for {user.username}! Please verify your email with the OTP sent.')
            return redirect('otp_verification', user_id=user.id)
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_verified:
                login(request, user)
                UserActivity.objects.create(user=user, action="Logged in")
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'Your account is not verified. Please verify your email.')
                return redirect('otp_verification', user_id=user.id)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate a new OTP for password reset
            user.otp = generate_otp()
            user.save()

            # Send OTP via email
            subject = 'Password Reset OTP - BtechTrader Academy'
            message = f'Your OTP to reset your password is: {user.otp}\n\nIf you did not request this, please ignore this email.'
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email,]
            send_mail(subject, message, email_from, recipient_list)

            messages.success(request, 'An OTP has been sent to your email to reset your password.')
            return redirect('reset_password', user_id=user.id)
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'accounts/forgot_password.html')

def reset_password(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        otp = request.POST.get('otp')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if user.otp != otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'accounts/reset_password.html', {'user': user})

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/reset_password.html', {'user': user})

        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'accounts/reset_password.html', {'user': user})

        # Update the user's password
        user.set_password(password1)
        user.otp = None  # Clear the OTP after successful reset
        user.save()

        # Log the activity
        UserActivity.objects.create(user=user, action="Reset password")

        messages.success(request, 'Your password has been reset successfully. Please log in with your new password.')
        return redirect('login')

    return render(request, 'accounts/reset_password.html', {'user': user})

def otp_verification(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        otp = request.POST.get('otp')
        if user.otp == otp:
            user.is_verified = True
            user.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account verified successfully!')
            UserActivity.objects.create(user=user, action="Verified account")
            return redirect('home')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    return render(request, 'accounts/otp_verification.html', {'user': user})

@login_required
def download_certificate(request, course_id, user_id):
    # Verify the user is requesting their own certificate
    if request.user.id != int(user_id):
        return HttpResponse("Unauthorized", status=403)

    # Fetch the course
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return HttpResponse("Course not found", status=404)

    # Check if the course is completed (optional, for security)
    lessons = Lesson.objects.filter(module__course=course)
    total_lessons = lessons.count()
    if total_lessons == 0:
        return HttpResponse("No lessons in this course", status=400)

    progress_records = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
    if not (all(record.progress_percentage == 100 for record in progress_records) and progress_records.count() == total_lessons):
        return HttpResponse("Course not completed", status=403)

    # Generate the PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Add content to the PDF
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 100, "Certificate of Completion")
    
    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 150, f"This certifies that")
    
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2, height - 200, f"{request.user.get_full_name() or request.user.username}")
    
    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 250, f"has successfully completed the course")
    
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 300, f"{course.title}")
    
    p.setFont("Helvetica", 14)
    p.drawCentredString(width / 2, height - 350, f"on {timezone.now().strftime('%B %d, %Y')}")
    
    # Add a border
    p.setStrokeColor(colors.black)
    p.setLineWidth(2)
    p.rect(50, 50, width - 100, height - 100, stroke=1, fill=0)

    p.showPage()
    p.save()

    # Prepare the response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{course_id}_{user_id}.pdf"'
    return response

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, 
                                 request.FILES, 
                                 instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            UserActivity.objects.create(user=request.user, action="Updated profile")
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    # Fetch enrolled courses
    enrollments = Enrollment.objects.filter(user=request.user, is_active=True)
    enrolled_courses = [enrollment.course for enrollment in enrollments]

    # Calculate course progress and completed courses
    course_progress = {}
    completed_courses = []
    for course in enrolled_courses:
        lessons = Lesson.objects.filter(module__course=course)
        total_lessons = lessons.count()
        if total_lessons == 0:
            course_progress[course.id] = 0
            continue

        progress_records = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
        total_progress = sum(record.progress_percentage for record in progress_records)
        course_progress_percentage = (total_progress / (total_lessons * 100)) * 100 if total_lessons > 0 else 0
        course_progress[course.id] = round(course_progress_percentage, 2)

        # Check if the course is completed (all lessons at 100%)
        if all(record.progress_percentage == 100 for record in progress_records) and progress_records.count() == total_lessons:
            completed_courses.append(course)

    # Auto-generated certificates for completed courses
    auto_certificates = [
        {
            'course': course,
            'certificate_url': f"/certificates/download/{course.id}/{request.user.id}/",
            'date_achieved': timezone.now(),
            'source': 'auto'
        }
        for course in completed_courses
    ]

    # Fetch admin-assigned certificates
    admin_certificates = Certificate.objects.filter(user=request.user)
    admin_certificates_data = [
        {
            'course': cert.course,
            'certificate_url': cert.get_certificate_url(),
            'date_achieved': cert.date_issued,
            'source': 'admin'
        }
        for cert in admin_certificates
    ]

    # Combine certificates
    certificates = auto_certificates + admin_certificates_data

    # Learning Statistics
    total_enrolled = len(enrolled_courses)
    total_completed = len(completed_courses)
    total_in_progress = total_enrolled - total_completed
    completed_lessons = LessonProgress.objects.filter(user=request.user, progress_percentage=100)
    total_time_spent = sum((lesson.lesson.duration for lesson in completed_lessons), timedelta())

    # Achievements
    achievements = []
    if total_completed >= 1:
        achievements.append({"name": "First Course Completed", "icon": "fas fa-trophy"})
    if total_enrolled >= 5:
        achievements.append({"name": "5 Courses Enrolled", "icon": "fas fa-star"})
    if total_completed >= 3:
        achievements.append({"name": "3 Courses Completed", "icon": "fas fa-medal"})

    # Recent Activities
    recent_activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')[:5]

    # Profile Completion
    profile_completion = request.user.profile.get_profile_completion()

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'enrolled_courses': enrolled_courses,
        'course_progress': course_progress,
        'completed_courses': completed_courses,
        'certificates': certificates,
        'last_active': request.user.last_login,
        'membership_status': 'Premium' if request.user.is_staff else 'Free',
        'learning_stats': {
            'total_enrolled': total_enrolled,
            'total_completed': total_completed,
            'total_in_progress': total_in_progress,
            'total_time_spent': total_time_spent,
        },
        'achievements': achievements,
        'recent_activities': recent_activities,
        'profile_completion': profile_completion,
    }
    return render(request, 'accounts/profile.html', context)



def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Save to database (optional)
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # Optionally send an email to the admin
        send_mail(
            subject,
            f"Message from {name} ({email}):\n\n{message}",
            email,
            ['guddukrbth0123@gmail.com'],
            fail_silently=False,
        )

        messages.success(request, 'Your message has been sent successfully!')
        return redirect('contact')

    return render(request, 'contact.html')