from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from .models import Course, CourseCategory, CourseModule, Lesson, Enrollment, LessonProgress, LessonBookmark, LessonViewAnalytics
from .forms import CourseForm, ModuleForm, LessonForm
from .payments import create_razorpay_order, send_payment_success_email, send_admin_notification
from django.contrib.auth.models import User
import json
import razorpay
import cloudinary.uploader
import logging
import time
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import google.generativeai as genai
from django.utils import timezone

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Set up logging
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def home(request):
    return render(request, "home.html")

def about(request):
    return render(request, "about.html")

def contact(request):
    return render(request, "contact.html")

def course_list(request):
    query = request.GET.get('q', '')
    
    if query:
        courses = Course.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        ).order_by('-created_at')
    else:
        courses = Course.objects.all().order_by('-created_at')
    
    categories = CourseCategory.objects.all()
    
    context = {
        'courses': courses,
        'categories': categories,
        'query': query,
    }
    return render(request, 'courses/course_list.html', context)

@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course.objects.prefetch_related('modules__lessons'), pk=pk)
    whatsapp_link = "https://wa.me/918084661813?text=Hi%20TradingPro%20Support,%20I%20need%20help%20with%20" + course.title.replace(' ', '%20')
    
    # Check if the user is enrolled, or if the course is free
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course, is_active=True).exists()
    
    # Auto-enroll user in free courses for progress tracking
    if course.is_free and not is_enrolled:
        Enrollment.objects.create(
            user=request.user,
            course=course,
            amount=0,
            payment_id=f"FREE_{course.id}_{request.user.id}"
        )
        is_enrolled = True  # Update is_enrolled after auto-enrollment

    # Fetch modules and lessons
    modules = course.modules.all().order_by('order')
    lessons = Lesson.objects.filter(module__course=course)
    total_lessons = lessons.count()

    # Calculate course progress (only if enrolled or free course)
    course_progress = 0
    lesson_progress = {}
    bookmarked_lessons = []
    last_lesson = None

    if is_enrolled or course.is_free:
        progress_records = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
        total_progress = sum(record.progress_percentage for record in progress_records)
        course_progress = (total_progress / (total_lessons * 100)) * 100 if total_lessons > 0 else 0

        # Fetch lesson progress and bookmarks
        lesson_progress = {p.lesson.id: p.progress_percentage for p in progress_records}
        bookmarked_lessons = LessonBookmark.objects.filter(user=request.user, lesson__in=lessons).values_list('lesson_id', flat=True)

        # Find the last lesson the user was on
        last_progress = LessonProgress.objects.filter(user=request.user, lesson__in=lessons).order_by('-last_watched').first()
        last_lesson = last_progress.lesson if last_progress else lessons.first()

    context = {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'whatsapp_link': whatsapp_link,
        'total_lessons': total_lessons,
        'lesson_progress': lesson_progress,
        'bookmarked_lessons': bookmarked_lessons,
        'course_progress': round(course_progress, 2),
        'last_lesson': last_lesson,
    }
    return render(request, 'courses/course_detail.html', context)

@login_required
def my_courses(request):
    # Fetch enrolled courses
    enrollments = Enrollment.objects.filter(user=request.user, is_active=True).select_related('course')
    enrolled_courses = [enrollment.course for enrollment in enrollments]
    enrolled_course_ids = [course.id for course in enrolled_courses]

    # Create a list of course data with progress, status, and last lesson
    course_data = []
    for course in enrolled_courses:
        lessons = Lesson.objects.filter(module__course=course)
        total_lessons = lessons.count()
        
        progress = 0
        status = 'Not Started'
        last_lesson = None

        if total_lessons > 0:
            progress_records = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
            total_progress = sum(record.progress_percentage for record in progress_records)
            progress = (total_progress / (total_lessons * 100)) * 100
            progress = round(progress, 2)

            if progress == 0:
                status = 'Not Started'
            elif progress == 100:
                status = 'Completed'
            else:
                status = 'In Progress'

            last_progress = LessonProgress.objects.filter(user=request.user, lesson__in=lessons).order_by('-last_watched').first()
            last_lesson = last_progress.lesson if last_progress else lessons.first()

        # Attach the computed values to the course object
        course.progress = progress
        course.status = status
        course.last_lesson = last_lesson
        course_data.append(course)

    # Search and filter
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'enrollment_date')

    courses = course_data
    if search_query:
        courses = [course for course in courses if search_query.lower() in course.title.lower()]

    if status_filter:
        courses = [course for course in courses if course.status == status_filter]

    if sort_by == 'progress':
        courses = sorted(courses, key=lambda x: x.progress, reverse=True)
    elif sort_by == 'title':
        courses = sorted(courses, key=lambda x: x.title.lower())
    else:
        # Sort by Enrollment ID as a proxy for enrollment order
        courses = sorted(courses, key=lambda x: Enrollment.objects.get(user=request.user, course=x).id, reverse=True)

    # Fetch recommended courses (not enrolled)
    recommended_courses = Course.objects.exclude(id__in=enrolled_course_ids).order_by('?')[:3]

    context = {
        'courses': courses,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'recommended_courses': recommended_courses,
    }
    return render(request, 'courses/my_courses.html', context)

def free_courses(request):
    courses = Course.objects.filter(is_free=True)
    context = {
        'courses': courses,
    }
    return render(request, 'courses/free_courses.html', context)

@user_passes_test(lambda u: u.is_staff)
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, 'Course added successfully!')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'courses/add_course.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
def add_lesson(request, module_id):
    module = get_object_or_404(CourseModule, id=module_id)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            video_file = request.FILES.get('video_file')

            try:
                if not video_file.name.lower().endswith(('.mp4', '.mov', '.avi')):
                    messages.error(request, "Please upload a valid video file (MP4, MOV, or AVI).")
                    return render(request, 'courses/add_lesson.html', {'form': form, 'module': module})
                
                upload_result = cloudinary.uploader.upload(
                    video_file,
                    resource_type="video",
                    folder="course_videos",
                    use_filename=True,
                    unique_filename=False
                )
                lesson.video_url = upload_result['secure_url']
                lesson.cloudinary_public_id = upload_result['public_id']
                logger.info(f"Uploaded video for lesson {lesson.title}: {lesson.video_url}")
            except Exception as e:
                logger.error(f"Video upload failed for lesson {lesson.title}: {str(e)}")
                messages.error(request, f"Video upload failed: {str(e)}")
                return render(request, 'courses/add_lesson.html', {'form': form, 'module': module})

            lesson.save()
            messages.success(request, 'Lesson added successfully!')
            return redirect('course_detail', pk=module.course.pk)
    else:
        form = LessonForm(initial={'module': module})
    return render(request, 'courses/add_lesson.html', {'form': form, 'module': module})

@login_required
def initiate_payment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        return redirect('course_detail', pk=course_id)
    
    request.session['course_id'] = course.id
    
    amount = int(course.discount_price if course.discount_price else course.price)
    order_amount = amount * 100
    
    order_data = {
        'amount': order_amount,
        'currency': 'INR',
        'payment_capture': 1,
        'notes': {
            'user_id': str(request.user.id),
            'course_id': str(course.id),
        }
    }
    
    try:
        order = client.order.create(data=order_data)
        context = {
            'course': course,
            'order': order,
            'amount': amount,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'user': request.user
        }
        return render(request, 'courses/payment.html', context)
    except Exception as e:
        logger.error(f"Payment initiation failed for course {course_id}: {str(e)}")
        return render(request, 'courses/payment_error.html', {'error': str(e)})

@login_required
def enroll_free_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_free=True)
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        Enrollment.objects.create(
            user=request.user,
            course=course,
            amount=0,
            payment_id=f"FREE_{course.id}_{request.user.id}"
        )
        messages.success(request, f"Enrolled in {course.title} successfully!")
    return redirect('course_detail', pk=course.id)

@csrf_exempt
def payment_webhook(request):
    if request.method == 'POST':
        payload = request.body
        data = json.loads(payload)
        
        try:
            client.utility.verify_payment_signature(data)
            
            if data['event'] == 'payment.captured':
                payment_id = data['payload']['payment']['entity']['id']
                order_id = data['payload']['payment']['entity']['order_id']
                amount = data['payload']['payment']['entity']['amount'] / 100
                
                order = client.order.fetch(order_id)
                user_id = order.get('notes', {}).get('user_id')
                course_id = order.get('notes', {}).get('course_id')
                
                if user_id and course_id:
                    user = get_object_or_404(User, id=user_id)
                    course = get_object_or_404(Course, id=course_id)
                    Enrollment.objects.create(
                        user=user,
                        course=course,
                        payment_id=payment_id,
                        amount=amount
                    )
                    send_payment_success_emails(user, course, amount)
                else:
                    logger.warning("User ID or Course ID not found in order metadata")
        
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
    
    return JsonResponse({'status': 'ok'})

def send_payment_success_emails(user, course, amount):
    subject_user = f"Successfully Purchased: {course.title}"
    html_message_user = render_to_string('courses/emails/payment_success_user.html', {
        'user': user,
        'course': course,
        'amount': amount
    })
    try:
        send_mail(
            subject_user,
            strip_tags(html_message_user),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message_user
        )
    except Exception as e:
        logger.error(f"Failed to send payment success email to user {user.email}: {str(e)}")
    
    subject_admin = f"New Course Purchase: {course.title}"
    message_admin = f"""
    New course purchase details:
    User: {user.username} ({user.email})
    Mobile: {user.mobile_number}
    Course: {course.title}
    Amount: ₹{amount}
    Payment ID: {Enrollment.objects.filter(course=course, user=user).first().payment_id}
    """
    try:
        send_mail(
            subject_admin,
            message_admin,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
        )
    except Exception as e:
        logger.error(f"Failed to send admin notification for course {course.title}: {str(e)}")

@login_required
def payment_success(request):
    course_id = request.session.get('course_id')
    if course_id:
        course = get_object_or_404(Course, id=course_id)
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            Enrollment.objects.create(
                user=request.user,
                course=course,
                payment_id=f"TEMP_{course.id}_{request.user.id}",
                amount=course.discount_price if course.discount_price else course.price
            )
        del request.session['course_id']
        messages.success(request, "Payment successful! You are now enrolled in the course.")
        return redirect('course_detail', pk=course_id)
    return redirect('profile')

@login_required
def toggle_bookmark(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    bookmark, created = LessonBookmark.objects.get_or_create(user=request.user, lesson=lesson)
    if not created:
        bookmark.delete()
        messages.success(request, f"Removed bookmark for {lesson.title}")
    else:
        messages.success(request, f"Bookmarked {lesson.title}")
    return redirect('course_detail', pk=lesson.module.course.pk)

@login_required
def update_progress(request):
    if request.method == 'POST':
        lesson_id = request.POST.get('lesson_id')
        progress = float(request.POST.get('progress', 0))
        if progress < 0 or progress > 100:
            logger.error(f"Invalid progress value {progress} for lesson {lesson_id}")
            return JsonResponse({'status': 'error', 'message': 'Invalid progress value'}, status=400)

        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        try:
            progress_obj, created = LessonProgress.objects.get_or_create(
                user=request.user,
                lesson=lesson,
                defaults={'progress_percentage': progress}
            )
            if not created:
                progress_obj.progress_percentage = max(progress_obj.progress_percentage, progress)
                progress_obj.save()
            
            LessonViewAnalytics.objects.create(lesson=lesson, user=request.user)
            logger.info(f"Progress updated for lesson {lesson_id}: {progress}%")
            return JsonResponse({'status': 'success', 'progress': progress_obj.progress_percentage})
        except Exception as e:
            logger.error(f"Failed to update progress for lesson {lesson_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def chat(request):
    # Check if the user wants to clear the chat
    if request.GET.get('clear') == 'true':
        request.session['chat_history'] = []
        request.session.modified = True
        return redirect('chat')

    chat_history = request.session.get('chat_history', [])
    error_message = None

    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()
        if not user_message:
            error_message = "Please enter a message."
        else:
            # Add user message to chat history with timestamp as string
            current_time = timezone.now()
            chat_history.append({
                'sender': 'user',
                'message': user_message,
                'timestamp': current_time.isoformat()  # Convert to string
            })

            # Check if the user is saying "Hi", "Hii", or "Hello"
            greeting_keywords = ['hi', 'hii', 'hello', 'hey']
            is_greeting = any(keyword in user_message.lower() for keyword in greeting_keywords)
            if is_greeting:
                ai_response = "Hello! How can I assist you with trading today?"
            else:
                # Check if the user is asking for the AI's name
                name_keywords = ['name', 'who are you', 'what is your name']
                is_name_query = any(keyword in user_message.lower() for keyword in name_keywords)
                if is_name_query:
                    ai_response = "I am BTech Trader Guru, here to help you with trading and stock-related questions!"
                else:
                    # Check if the message is related to trading/stocks
                    trading_keywords = [
                        'trading', 'stock', 'stocks', 'invest', 'investment', 'market', 'markets',
                        'share', 'shares', 'equity', 'portfolio', 'bull', 'bear', 'dividend',
                        'ipo', 'etf', 'mutual fund', 'bond', 'bonds', 'option', 'options',
                        'future', 'futures', 'forex', 'currency', 'commodity', 'commodities',
                        'technical analysis', 'fundamental analysis', 'price', 'volume', 'trend',
                        'strategy', 'strategies', 'risk', 'return', 'profit', 'loss', 'broker',
                        'exchange', 'nse', 'bse', 'nasdaq', 'nyse', 'dow', 's&p', 'index'
                    ]
                    is_trading_related = any(keyword in user_message.lower() for keyword in trading_keywords)

                    if not is_trading_related:
                        ai_response = "Sorry, I can only assist with questions related to trading and stocks. Please ask something about trading or stocks!"
                    else:
                        try:
                            # System prompt to enforce trading/stock focus and AI identity
                            system_prompt = (
                                "You are BTech Trader Guru, an AI assistant specialized in trading and stocks. "
                                "Only respond to questions related to trading, stocks, investments, markets, or related financial topics. "
                                "If the user asks about unrelated topics, politely decline to answer and remind them to ask about trading or stocks. "
                                "Do not reveal your identity unless explicitly asked."
                            )
                            prompt = f"{system_prompt}\nUser: {user_message}\nAssistant:"
                            response = model.generate_content(prompt)
                            ai_response = response.text.strip()
                        except Exception as e:
                            logger.error(f"Gemini API error: {str(e)}")
                            ai_response = "Sorry, there was an error processing your request. Please try again later."

            # Add AI response to chat history with timestamp as string
            chat_history.append({
                'sender': 'ai',
                'message': ai_response,
                'timestamp': timezone.now().isoformat()  # Convert to string
            })

        # Save chat history to session
        request.session['chat_history'] = chat_history
        request.session.modified = True

    context = {
        'chat_history': chat_history,
        'error_message': error_message,
    }
    return render(request, 'courses/chat.html', context)