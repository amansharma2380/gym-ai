from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('make-payment/', views.make_payment, name='make_payment'),
    path('admin/payments/', views.admin_payments, name='admin_payments'),
    path('generate-plan/', views.generate_plan, name='generate_plan'),
    path('generate-plan/<int:member_id>/', views.generate_plan, name='generate_plan_member'),
    path('api/progress-data/', views.progress_data, name='progress_data'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
path('progress/add/', views.add_progress, name='add_progress'),
path('api/v1/progress/', views.api_progress_list, name='api_progress_list'),
path('plan/delete/<int:id>/', views.delete_plan, name='delete_plan'),
path('ajax/generate-plan/', views.generate_plan_ajax, name='generate_plan_ajax'),
path('ajax/delete-plan/<int:plan_id>/', views.delete_plan_ajax, name='delete_plan_ajax'),
path('progress/photos/upload/', views.upload_progress_photo, name='upload_progress_photo'),
path('ajax/ai-coach/', views.ai_coach_ajax, name='ai_coach_ajax'),

]
