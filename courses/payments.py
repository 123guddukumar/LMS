import razorpay
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_razorpay_order(amount, currency="INR"):
    data = {
        "amount": amount * 100,  # Razorpay expects amount in paise
        "currency": currency,
        "payment_capture": 1  # Auto capture payment
    }
    return client.order.create(data=data)

def send_payment_success_email(user, course):
    subject = f"Successfully Purchased: {course.title}"
    html_message = render_to_string('courses/payment_success_email.html', {
        'user': user,
        'course': course,
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message
    )

def send_admin_notification(user, course):
    subject = f"New Course Purchase: {course.title}"
    message = f"""
    New course purchase:
    User: {user.username}
    Email: {user.email}
    Mobile: {user.mobile_number}
    Course: {course.title}
    Price: {course.price}
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
    )