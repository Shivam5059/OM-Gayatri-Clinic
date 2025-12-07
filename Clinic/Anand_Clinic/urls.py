from . import views
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.urls import path,reverse_lazy
from .views import (
    RoleBasedLoginView,DoctorDashboard,HomePageView, AddPatient, PatientsView, PatientDetailView, FollowUpsView, PharmacyView, CheckInsView,
    MedicineListView, MedicineCreateView, MedicineUpdateView, MedicineDetailView,
    PrescriptionGeneratorCreateView, PrescriptionGeneratorUpdateView, PrescriptionGeneratorDetailView,
    PrescriptionGeneratorListView
)

app_name = 'Anand_Clinic'
urlpatterns = [
    # redirect root URL to login page
    path('', lambda request: redirect('Anand_Clinic:login'), name='home_redirect'),

    # login URL
    path('accounts/login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),

    # dashboards
    path('doctor/dashboard/', DoctorDashboard.as_view(), name='doctor_dashboard'),

    # Patient routes
    path('home/', HomePageView.as_view(), name='index'),
    path('add_patient/', AddPatient.as_view(), name='add_patient'),
    path('patient_list/', PatientsView.as_view(), name='patient_list'),
    path('detail/<int:pk>/', PatientDetailView.as_view(), name='patient_details'),
    path('follow-ups/', FollowUpsView.as_view(), name='follow_ups'),
    path('check-ins/', CheckInsView.as_view(), name='checkin_list'),
    
    # Pharmacy routes
    path('pharmacy/', PharmacyView.as_view(), name='pharmacy'),
    
    # Medicine routes
    path('pharmacy/medicines/', MedicineListView.as_view(), name='medicine_list'),
    path('pharmacy/medicines/add/', MedicineCreateView.as_view(), name='medicine_add'),
    path('pharmacy/medicines/<int:pk>/', MedicineDetailView.as_view(), name='medicine_detail'),
    path('pharmacy/medicines/<int:pk>/edit/', MedicineUpdateView.as_view(), name='medicine_edit'),
    path('pharmacy/medicines/<int:pk>/dispense/', views.dispense_medicine_ajax, name='medicine_dispense_ajax'),
    path('pharmacy/medicines/<int:pk>/update_stock/', views.update_stock_ajax, name='medicine_update_stock_ajax'),
    
    path('prescription-generator/', PrescriptionGeneratorCreateView.as_view(), name='prescription_generator_create'),
    path('prescription-generator/<int:pk>/edit/', PrescriptionGeneratorUpdateView.as_view(), name='prescription_generator_edit'),
    path('prescription-generator/<int:pk>/', PrescriptionGeneratorDetailView.as_view(), name='prescription_generator_detail'),
    path('prescription-generator/list/', PrescriptionGeneratorListView.as_view(), name='prescription_generator_list'),

    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<uuid:token>/", views.reset_password, name="reset_password"),

    # followup...
    path('followups/create-ajax/', views.create_followup_ajax, name='followup_create_ajax'),
    path('followups/checkin-ajax/', views.create_checkin_ajax, name='followup_checkin_ajax'),

    #ADD THIS — needed for auto-refresh of patient list
    path('ajax/patients/', views.ajax_patient_list, name='ajax_patient_list'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),

# User enters UID + token manually
    path("password-reset-manual/", views.manual_reset, name="password_reset_manual"),

    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]
