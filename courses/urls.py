from django.urls import path
from .views import (
    home, about, contact, course_list, course_detail, free_courses, 
    add_course, add_lesson, initiate_payment, enroll_free_course, 
    payment_webhook, payment_success, toggle_bookmark, update_progress, 
    my_courses
)

urlpatterns = [
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('courses/', course_list, name='course_list'),
    path('courses/<int:pk>/', course_detail, name='course_detail'),
    path('courses/free/', free_courses, name='free_courses'),
    path('courses/add/', add_course, name='add_course'),
    path('modules/<int:module_id>/add-lesson/', add_lesson, name='add_lesson'),
    path('courses/<int:course_id>/initiate-payment/', initiate_payment, name='initiate_payment'),
    path('courses/<int:course_id>/enroll-free/', enroll_free_course, name='enroll_free_course'),
    path('payment-webhook/', payment_webhook, name='payment_webhook'),
    path('payment-success/', payment_success, name='payment_success'),
    path('lessons/<int:lesson_id>/toggle-bookmark/', toggle_bookmark, name='toggle_bookmark'),
    path('update-progress/', update_progress, name='update_progress'),
    path('my-courses/', my_courses, name='my_courses'),
    # path('chat/', chat, name='chat'),
]