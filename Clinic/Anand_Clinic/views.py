import datetime
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView, CreateView, UpdateView
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.urls import reverse_lazy,reverse
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from .forms import PatientForm, MedicineForm, SimpleMedicineForm, PrescriptionGeneratorForm
from .models import FollowUp, Patient, Medicine, CheckIn, StockTransaction, Prescription, FirstDayInstruction, NextDayInstruction,User,Profile
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.template.loader import render_to_string

# Anand_Clinic/views.py
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from .utils import group_required
from django.contrib.auth.views import LoginView,LogoutView
from django.shortcuts import render, redirect   
from django.urls import reverse_lazy
from django.contrib.auth.forms import AuthenticationForm

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from urllib.parse import quote
from datetime import timedelta
from .models import Profile, PasswordResetToken
from .forms import ForgotPasswordForm, ResetPasswordForm

def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            number = form.cleaned_data['whatsapp']

            try:
                profile = Profile.objects.get(whatsapp=number)
                user = profile.user

                reset_token = PasswordResetToken.objects.create(user=user)
                reset_link = request.build_absolute_uri(f"/reset-password/{reset_token.token}/")

                # WhatsApp msg text
                msg = f"Reset your password using this link: {reset_link}"

                # WhatsApp URL
                whatsapp_url = f"https://wa.me/{profile.country_code}{profile.whatsapp}?text={msg}"

                messages.success(request, "Reset link generated! Click below to send on WhatsApp.")
                return render(request, "forgot_password.html", {
                    "form": form,
                    "whatsapp_url": whatsapp_url
                })

            except Profile.DoesNotExist:
                messages.error(request, "Mobile number not found!")

    else:
        form = ForgotPasswordForm()

    return render(request, "forgot_password.html", {"form": form})


def reset_password(request, token):
    token_obj = get_object_or_404(PasswordResetToken, token=token, is_used=False)

    if timezone.now() > token_obj.created_at + timedelta(hours=1):
        messages.error(request, "Link expired!")
        return redirect("forgot_password")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_pwd = form.cleaned_data['new_password']
            confirm = form.cleaned_data['confirm_password']

            if new_pwd != confirm:
                messages.error(request, "Passwords do not match!")
            else:
                user = token_obj.user
                user.set_password(new_pwd)
                user.save()
                token_obj.is_used = True
                token_obj.save()
                messages.success(request, "Password reset successful!")
                return redirect("login")
    else:
        form = ResetPasswordForm()

    return render(request, "reset_password.html", {"form": form})

def manual_reset(request):
    if request.method == "POST":
        username = request.POST.get("username")
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Validate fields
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("Anand_Clinic:password_reset_manual")

        # Verify user
        user = authenticate(username=username, password=current_password)
        if user is None:
            messages.error(request, "Invalid current password.")
            return redirect("Anand_Clinic:password_reset_manual")

        # SUCCESS — reset password
        user.set_password(new_password)
        user.save()

        logout(request)  # <-- REQUIRED

        messages.success(request, "Password reset successful. Please login again.")
        return redirect("Anand_Clinic:login")

    return render(request, "password_reset_manual.html")

def logout_user(request):
    logout(request)
    return redirect('Anand_Clinic:login')

def home_redirect(request):
    # redirect root URL to 'home'
    return redirect('Anand_Clinic:index')

class RoleBasedLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = AuthenticationForm
    
    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            if user.groups.filter(name="Receptionist").exists():
                return redirect("/add_patient/")
            elif user.groups.filter(name="Doctor").exists():
                return redirect("/doctor/dashboard/")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("Anand_Clinic:login")
        return render(request, self.template_name, {"error": "Invalid login"})

    def get_context_data(self, **kwargs):
        # Ensure form is always present in template
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.authentication_form()
        return context
    
class DoctorDashboard(LoginRequiredMixin, ListView):
    model = Patient
    # use the clinic.html home template (your HomePageView uses this)
    template_name = 'clinic.html'
    context_object_name = 'patients'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name="Doctor").exists():
            return redirect("Anand_Clinic:add_patient")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Patient.objects.all().order_by("-appointment_date")
    
# Create your views here.

class HomePageView(LoginRequiredMixin,TemplateView):
    login_url = '/accounts/login/'
    template_name = 'clinic.html'   #this will tell django look for a template name home.html

    model = Patient
    
    def get_context_data(self, **kwargs):    
        context =  super().get_context_data(**kwargs)
        # newest patients first
        patients = Patient.objects.prefetch_related('followups').all().order_by('-appointment_date')
        # Add has_scheduled_followup flag to each patient
        for patient in patients:
            patient.has_scheduled_followup = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).exists()
        context ['patients'] = patients
        # Add all follow-ups to context
        context['followups'] = FollowUp.objects.select_related('patient').filter(
            status=FollowUp.STATUS_SCHEDULED
        ).order_by('scheduled_date')[:10]
        # Add today's check-ins
        today = timezone.now().date()
        context['today_checkins'] = CheckIn.objects.select_related('followup__patient').filter(
            checkin_time__date=today
        ).order_by('-checkin_time')[:20]
        return context 

class AddPatient(FormView):
    model = Patient
    form_class = PatientForm
    template_name = 'add_new_patient.html'
    success_url = reverse_lazy('Anand_Clinic:patient_list') 

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f'Patient "{self.object.name}" added successfully!')
        return redirect('Anand_Clinic:patient_list')

class PatientsView(ListView):
    template_name = 'patient_list.html'
    model = Patient

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        patients = Patient.objects.prefetch_related('followups').all().order_by('-appointment_date')
        # Add has_scheduled_followup flag to each patient
        for patient in patients:
            patient.has_scheduled_followup = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).exists()
        context ['patients'] = patients
        return context 
    
class PatientDetailView(DetailView):
    template_name = 'detail.html'
    model = Patient

class FollowUpsView(TemplateView):
    template_name = 'follow_ups.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followups'] = FollowUp.objects.select_related('patient').order_by('-scheduled_date')
        return context

class CheckInsView(ListView):
    model = CheckIn
    template_name = 'checkin_list.html'
    context_object_name = 'checkins'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = CheckIn.objects.select_related('followup__patient').order_by('-checkin_time')
        search_query = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        date_filter = self.request.GET.get('date', '')
        # Single scheduled and checkin filters (date or datetime)
        scheduled = self.request.GET.get('scheduled', '')
        checkin = self.request.GET.get('checkin', '')
        doctor = self.request.GET.get('doctor', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(followup__patient__name__icontains=search_query) |
                Q(followup__patient__case_no__icontains=search_query)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_filter:
            queryset = queryset.filter(checkin_time__date=date_filter)

        # Parse a single date/datetime string and return a date object
        def _parse_to_date(val):
            if not val:
                return None
            dt = parse_datetime(val)
            if dt:
                return dt.date()
            d = parse_date(val)
            if d:
                return d
            return None

        s_date = _parse_to_date(scheduled)
        if s_date:
            queryset = queryset.filter(followup__scheduled_date__date=s_date)

        c_date = _parse_to_date(checkin)
        if c_date:
            queryset = queryset.filter(checkin_time__date=c_date)
        
        if doctor:
            # Handle both old format (full name) and new format (code)
            if doctor == 'dr_1':
                queryset = queryset.filter(
                    Q(followup__patient__doctor='dr_1') |
                    Q(followup__patient__doctor='Dr Ami Bhatt')
                )
            elif doctor == 'dr_2':
                queryset = queryset.filter(
                    Q(followup__patient__doctor='dr_2') |
                    Q(followup__patient__doctor='Dr Kaushal Bhatt')
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_checkins'] = CheckIn.objects.count()
        context['early_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_EARLY).count()
        context['on_time_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_ON_TIME).count()
        context['late_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_LATE).count()
        context['doctor_choices'] = [('dr_1', 'Dr. Ami Bhatt'), ('dr_2', 'Dr. Kaushal Bhatt')]
        # Count check-ins by doctor - handle both old format (full name) and new format (code)
        context['ami_count'] = CheckIn.objects.filter(
            Q(followup__patient__doctor='dr_1') |
            Q(followup__patient__doctor='Dr Ami Bhatt')
        ).count()
        context['kaushal_count'] = CheckIn.objects.filter(
            Q(followup__patient__doctor='dr_2') |
            Q(followup__patient__doctor='Dr Kaushal Bhatt')
        ).count()
        return context

class PharmacyView(TemplateView):
    template_name = 'pharmacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['medicines'] = Medicine.objects.all()[:10]
        context['low_stock_medicines'] = Medicine.objects.filter(
            stock_quantity__lte=F('reorder_level')
        )[:5]
        context['total_medicines'] = Medicine.objects.count()
        context['total_patients'] = Patient.objects.count()
        # Add all patients and medicines for inline forms
        context['all_patients'] = Patient.objects.all().order_by('name')
        context['all_medicines'] = Medicine.objects.all().order_by('name')
        return context


# Medicine Views
class MedicineListView(ListView):
    model = Medicine
    template_name = 'medicine_list.html'
    context_object_name = 'medicines'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Medicine.objects.all()
        search_query = self.request.GET.get('search', '')
        medicine_type = self.request.GET.get('type', '')
        low_stock = self.request.GET.get('low_stock', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(generic_name__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        if medicine_type:
            queryset = queryset.filter(medicine_type=medicine_type)
        
        if low_stock == 'true':
            queryset = queryset.filter(stock_quantity__lte=F('reorder_level'))
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['low_stock_count'] = Medicine.objects.filter(
            stock_quantity__lte=F('reorder_level')
        ).count()
        context['expired_count'] = Medicine.objects.filter(
            expiry_date__lt=timezone.now().date()
        ).count()
        return context


class MedicineCreateView(CreateView):
    model = Medicine
    # Use simplified form for quick add (only name and quantity)
    form_class = SimpleMedicineForm
    template_name = 'medicine_form.html'
    success_url = reverse_lazy('Anand_Clinic:medicine_list')
    
    def form_valid(self, form):
        # Save object first
        self.object = form.save()
        messages.success(self.request, f'Medicine "{form.cleaned_data["name"]}" added successfully!')
        # Handle AJAX requests: return JSON with created object summary
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'id': self.object.pk,
                'name': self.object.name,
                'stock_quantity': self.object.stock_quantity,
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        # Return JSON errors for AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


@require_POST
def dispense_medicine_ajax(request, pk):
    """AJAX endpoint to reduce medicine stock.

    Expects POST: quantity (int), optional reason
    Returns JSON: { success: True, new_stock: int }
    """
    try:
        med = Medicine.objects.get(pk=pk)
    except Medicine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Medicine not found.'}, status=404)

    qty = request.POST.get('quantity')
    reason = request.POST.get('reason', 'dispensed')

    try:
        qty = int(qty)
        if qty <= 0:
            raise ValueError()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid quantity.'}, status=400)

    # reduce stock (never negative)
    removed = min(qty, med.stock_quantity)
    med.stock_quantity = med.stock_quantity - removed
    med.save(update_fields=['stock_quantity'])

    # Record stock transaction
    StockTransaction.objects.create(
        medicine=med,
        change=-removed,
        reason=reason
    )

    return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'removed': removed})


@require_POST
def update_stock_ajax(request, pk):
    """AJAX endpoint to add or set medicine stock.

    Expects POST: quantity (int), mode ('add' or 'set'), optional reason
    Returns JSON: { success: True, new_stock: int, delta: int }
    """
    try:
        med = Medicine.objects.get(pk=pk)
    except Medicine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Medicine not found.'}, status=404)

    qty = request.POST.get('quantity')
    mode = request.POST.get('mode', 'add')
    reason = request.POST.get('reason', 'stock_update')

    try:
        qty = int(qty)
        if qty < 0:
            raise ValueError()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid quantity.'}, status=400)

    if mode == 'add':
        delta = qty
        med.stock_quantity = med.stock_quantity + delta
        med.save(update_fields=['stock_quantity'])
        StockTransaction.objects.create(medicine=med, change=delta, reason=reason)
        return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'delta': delta})
    elif mode == 'set':
        old = med.stock_quantity
        med.stock_quantity = qty
        med.save(update_fields=['stock_quantity'])
        delta = med.stock_quantity - old
        StockTransaction.objects.create(medicine=med, change=delta, reason=reason)
        return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'delta': delta})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid mode.'}, status=400)


class MedicineUpdateView(UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicine_form.html'
    success_url = reverse_lazy('Anand_Clinic:medicine_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Medicine "{form.instance.name}" updated successfully!')
        response = super().form_valid(form)
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(status=200)
        return response


class MedicineDetailView(DetailView):
    model = Medicine
    template_name = 'medicine_detail.html'
    context_object_name = 'medicine'



# my code for follow-up...

@require_POST
def create_followup_ajax(request):
    """
    Expects: patient_id, scheduled_date (from input type=datetime-local -> "YYYY-MM-DDTHH:MM")
    Returns JSON: { success: true, followup: {...} } or { success: false, error: "..." }
    This version does NOT require login. created_by will be set only if request.user.is_authenticated.
    """
    patient_id = request.POST.get('patient_id')
    scheduled_date_str = request.POST.get('scheduled_date')

    if not patient_id or not scheduled_date_str:
        return JsonResponse({'success': False, 'error': 'Missing patient or date.'}, status=400)

    try:
        patient = Patient.objects.get(pk=int(patient_id))
    except (Patient.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Patient not found.'}, status=404)

    # parse datetime-local string. It typically has no timezone info.
    try:
        if len(scheduled_date_str.split(':')) == 2:
            scheduled_date_str = scheduled_date_str + ':00'
        dt = parse_datetime(scheduled_date_str)
        if dt is None:
            dt = datetime.fromisoformat(scheduled_date_str)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)

    # Make timezone-aware if naive
    if timezone.is_naive(dt):
        current_tz = timezone.get_current_timezone()
        dt = timezone.make_aware(dt, current_tz)

    # Validate date not in past
    if dt < timezone.now():
        return JsonResponse({'success': False, 'error': 'Cannot schedule a follow-up in the past.'}, status=400)

    # Check for existing scheduled follow-up
    existing = FollowUp.objects.filter(patient=patient, status=FollowUp.STATUS_SCHEDULED)
    if existing.exists():
        return JsonResponse({'success': False, 'error': 'Patient already has a scheduled follow-up.'}, status=400)

    # Create follow-up; set created_by only if authenticated
    try:
        created_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        fu = FollowUp.objects.create(
            patient=patient,
            scheduled_date=dt,
            created_by=created_by,
            status=FollowUp.STATUS_SCHEDULED
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    local_scheduled = timezone.localtime(fu.scheduled_date)
    scheduled_attr = local_scheduled.strftime('%Y-%m-%d %H:%M')
    scheduled_display = local_scheduled.strftime('%b %d, %Y %H:%M')

    return JsonResponse({
        'success': True,
        'followup': {
            'id': fu.pk,
            'patient_id': patient.pk,
            'patient_name': getattr(patient, 'name', str(patient)),
            'doctor_display': patient.get_doctor_display(),
            'scheduled_date': fu.scheduled_date.isoformat(),
            'scheduled_date_attr': scheduled_attr,
            'scheduled_date_display': scheduled_display,
            'status': fu.status,
        }
    })


@require_POST
def create_checkin_ajax(request):
    """AJAX endpoint to record a check-in for a follow-up.
    Expects: followup_id
    Returns JSON with checkin status: early/on_time/late and minutes difference.
    """
    followup_id = request.POST.get('followup_id')
    if not followup_id:
        return JsonResponse({'success': False, 'error': 'Missing followup id.'}, status=400)

    try:
        fu = FollowUp.objects.select_related('patient').get(pk=int(followup_id))
    except (FollowUp.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Follow-up not found.'}, status=404)

    now = timezone.now()
    scheduled = fu.scheduled_date
    # Ensure both are timezone-aware
    if timezone.is_naive(scheduled):
        scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())

    diff = (now - scheduled).total_seconds()
    minutes = int(diff // 60)

    if diff < 0:
        status = CheckIn.STATUS_EARLY
    elif diff > 3 * 3600:
        status = CheckIn.STATUS_LATE
    else:
        status = CheckIn.STATUS_ON_TIME

    created_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

    checkin = CheckIn.objects.create(
        followup=fu,
        checkin_time=now,
        status=status,
        minutes_difference=minutes,
        created_by=created_by
    )

    local_checkin = timezone.localtime(checkin.checkin_time)
    checkin_time_attr = local_checkin.strftime('%Y-%m-%d %H:%M')
    checkin_time_display = local_checkin.strftime('%b %d, %Y %H:%M')

    # Optionally mark follow-up as completed on check-in
    try:
        # Save check-in fields on the follow-up for direct reference
        fu.checkin_time = now
        fu.checkin_status = status
        fu.checkin_minutes_difference = minutes
        fu.checkin_by = created_by
        fu.status = FollowUp.STATUS_COMPLETED
        fu.save(update_fields=['checkin_time', 'checkin_status', 'checkin_minutes_difference', 'checkin_by', 'status'])
    except Exception:
        pass

    return JsonResponse({
        'success': True,
        'checkin': {
            'id': checkin.pk,
            'followup_id': fu.pk,
            'patient_name': fu.patient.name,
            'doctor_display': fu.patient.get_doctor_display(),
            'checkin_time': checkin.checkin_time.isoformat(),
            'checkin_time_attr': checkin_time_attr,
            'checkin_time_display': checkin_time_display,
            'status': checkin.status,
            'minutes_difference': checkin.minutes_difference,
        }
    })
class PrescriptionGeneratorCreateView(TemplateView):
    template_name = 'prescription_generator_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PrescriptionGeneratorForm()
        context['patients'] = Patient.objects.all().order_by('name')
        return context

    def post(self, request, *args, **kwargs):
        form = PrescriptionGeneratorForm(request.POST)
        if form.is_valid():
            patient = form.cleaned_data['patient']
            case_number = form.cleaned_data['case_number']
            prescription = Prescription.objects.create(
                patient=patient,
                case_number=case_number,
                prescribed_by_ami=bool(request.POST.get('doctor_ami')),
                prescribed_by_kaushal=bool(request.POST.get('doctor_kaushal')),
                language=request.POST.get('language', 'en')
            )

            first_total = int(request.POST.get('first_TOTAL', '0') or '0')
            for i in range(first_total):
                size = request.POST.get(f'first-{i}-size')
                label = request.POST.get(f'first-{i}-label')
                pills = request.POST.get(f'first-{i}-pills')
                time = request.POST.get(f'first-{i}-time')
                special = request.POST.get(f'first-{i}-special', '')
                if size and label and pills and time:
                    FirstDayInstruction.objects.create(
                        prescription=prescription,
                        size_of_bottle=size,
                        label=label,
                        no_of_pill=pills,
                        time_of_day=time,
                        special_instruction=special,
                    )

            next_total = int(request.POST.get('next_TOTAL', '0') or '0')
            for i in range(next_total):
                bottle_no = request.POST.get(f'next-{i}-bottle')
                pills = request.POST.get(f'next-{i}-pills')
                dose = request.POST.get(f'next-{i}-dose')
                time = request.POST.get(f'next-{i}-time')
                if bottle_no and pills and dose and time:
                    NextDayInstruction.objects.create(
                        prescription=prescription,
                        bottle_no=bottle_no,
                        no_of_pill=pills,
                        dose=dose,
                        time_of_day=time,
                    )

            return redirect('Anand_Clinic:prescription_generator_detail', pk=prescription.pk)
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class PrescriptionGeneratorUpdateView(TemplateView):
    template_name = 'prescription_generator_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PrescriptionGeneratorForm()
        context['patients'] = Patient.objects.all().order_by('name')
        context['prescription'] = Prescription.objects.get(pk=self.kwargs['pk'])
        return context

    def post(self, request, *args, **kwargs):
        prescription = Prescription.objects.get(pk=self.kwargs['pk'])
        form = PrescriptionGeneratorForm(request.POST)
        if form.is_valid():
            prescription.patient = form.cleaned_data['patient']
            prescription.case_number = form.cleaned_data['case_number']
            prescription.prescribed_by_ami = bool(request.POST.get('doctor_ami'))
            prescription.prescribed_by_kaushal = bool(request.POST.get('doctor_kaushal'))
            prescription.language = request.POST.get('language', prescription.language)
            prescription.save()

            prescription.first_day_instructions.all().delete()
            prescription.next_day_instructions.all().delete()

            first_total = int(request.POST.get('first_TOTAL', '0') or '0')
            for i in range(first_total):
                size = request.POST.get(f'first-{i}-size')
                label = request.POST.get(f'first-{i}-label')
                pills = request.POST.get(f'first-{i}-pills')
                time = request.POST.get(f'first-{i}-time')
                special = request.POST.get(f'first-{i}-special', '')
                if size and label and pills and time:
                    FirstDayInstruction.objects.create(
                        prescription=prescription,
                        size_of_bottle=size,
                        label=label,
                        no_of_pill=pills,
                        time_of_day=time,
                        special_instruction=special,
                    )

            next_total = int(request.POST.get('next_TOTAL', '0') or '0')
            for i in range(next_total):
                bottle_no = request.POST.get(f'next-{i}-bottle')
                pills = request.POST.get(f'next-{i}-pills')
                dose = request.POST.get(f'next-{i}-dose')
                time = request.POST.get(f'next-{i}-time')
                if bottle_no and pills and dose and time:
                    NextDayInstruction.objects.create(
                        prescription=prescription,
                        bottle_no=bottle_no,
                        no_of_pill=pills,
                        dose=dose,
                        time_of_day=time,
                    )

            return redirect('Anand_Clinic:prescription_generator_detail', pk=prescription.pk)
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class PrescriptionGeneratorDetailView(TemplateView):
    template_name = 'prescription_generator_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        p = Prescription.objects.get(pk=self.kwargs['pk'])
        lines = []
        if p.language == 'gu':
            size_map = {'small': 'નાની', 'medium': 'મધ્યમ', 'large': 'મોટી'}
            dose_map = {'one': 'એક', 'two': 'બે', 'three': 'ત્રણ', 'four': 'ચાર', 'five': 'પાંચ'}
            time_map = {'Day': 'દિવસ', 'Morning': 'સવારે', 'Night': 'રાત્રે'}
            lines.append('દવા લેવાની રીત')
            lines.append('To,')
            lines.append(f"{p.patient.name} (કેસ નંબર. {p.case_number}),")
            lines.append('તમારે નીચે મુજબ હોમિયોપેથીની દવા લેવી છે:')
            lines.append('')
            lines.append('પહેલા દિવસે:')
            for fd in p.first_day_instructions.all():
                size = size_map.get(fd.size_of_bottle, fd.size_of_bottle)
                time = time_map.get(fd.time_of_day, fd.time_of_day)
                base = f"☑ {size} બોટલ: ‘{fd.label}’ તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} ગોળીઓ લો."
                if fd.special_instruction:
                    base = f"☑ {size} બોટલ: ‘{fd.label}’ તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} ગોળીઓ લો {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append('આગલા દિવસોથી આગળ:')
            for nd in p.next_day_instructions.all():
                time = time_map.get(nd.time_of_day, nd.time_of_day)
                dose = dose_map.get(nd.dose, nd.dose)
                lines.append(f"☑ બોટલ નંબર. {nd.bottle_no} માંથી: {nd.no_of_pill} ગોળી, દિવસમાં {dose} વાર. રોજ {time}.")
        else:
            lines.append('Instructions for Medicinal Distribution')
            lines.append('To,')
            lines.append(f"{p.patient.name} (Case No. {p.case_number}),")
            lines.append('You have to take Homeopathic medicine in the following order:')
            lines.append('')
            lines.append('On first day:')
            for fd in p.first_day_instructions.all():
                base = f"☑ {fd.size_of_bottle} bottle: Labeled as ‘{fd.label}’: take {fd.no_of_pill} pills at {fd.time_of_day}."
                if fd.special_instruction:
                    base = f"☑ {fd.size_of_bottle} bottle: Labeled as ‘{fd.label}’: take {fd.no_of_pill} pills at {fd.time_of_day} {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append('From Next day onwards:')
            for nd in p.next_day_instructions.all():
                lines.append(f"☑ From Bottle No. {nd.bottle_no}: {nd.no_of_pill} pills, {nd.dose} times a {nd.time_of_day}.")
        lines.append('')
        doctor_names = []
        if p.prescribed_by_ami:
            doctor_names.append('Dr. Ami Bhatt')
        if p.prescribed_by_kaushal:
            doctor_names.append('Dr. Kaushal Bhatt')
        if len(doctor_names) == 2:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        elif len(doctor_names) == 1:
            lines.append(doctor_names[0])
        else:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        context['formatted'] = "\n".join(lines)
        context['prescription'] = p
        return context


class PrescriptionGeneratorListView(ListView):
    model = Prescription
    template_name = 'prescription_generator_list.html'
    context_object_name = 'prescriptions'
    paginate_by = 20

    def get_queryset(self):
        qs = Prescription.objects.select_related('patient').order_by('-created_at')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(patient__name__icontains=q) |
                Q(case_number__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_prescriptions'] = Prescription.objects.count()
        return context

@login_required
def ajax_patient_list(request):
    """Return rendered HTML of the patient list."""
    patients = Patient.objects.prefetch_related('followups').all().order_by('-appointment_date')
    for patient in patients:
        patient.has_scheduled_followup = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).exists()
    
    html = render_to_string('partials/patient_list_items.html', {'patients': patients})
    return JsonResponse({'html': html})

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")   # whatever your home page is
        else:
            messages.error(request, "Incorrect username or password")

    return render(request, "login.html")
