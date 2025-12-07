from django import forms 
from django.core.validators import RegexValidator
import re
from .models import Medicine, Patient

class ForgotPasswordForm(forms.Form):
    whatsapp = forms.CharField(
        max_length=15,
        label="Mobile Number",
        widget=forms.TextInput(attrs={"placeholder": "Enter registered WhatsApp number"})
    )

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New Password"}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"}),
        label="Confirm Password"
    )
    
class PrescriptionGeneratorForm(forms.Form):
    patient = forms.ModelChoiceField(queryset=Patient.objects.all())
    case_number = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly': 'readonly'}))
    instruction_type = forms.ChoiceField(choices=[('first', 'First Day Instructions'), ('next', 'From Next Day Onwards')])

DOCTOR_CHOICES = [
    ('dr_1','Dr. Ami Bhatt'),
    ('dr_2','Dr. Kaushal Bhatt'),
]
GENDER = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')]

MEDICINE_TYPE_CHOICES = [
    ('tablet', 'Tablet'),
    ('capsule', 'Capsule'),
    ('syrup', 'Syrup'),
    ('injection', 'Injection'),
    ('ointment', 'Ointment'),
    ('drops', 'Drops'),
    ('other', 'Other'),
]


class PatientForm(forms.ModelForm):
        case = forms.CharField()
        name = forms.CharField()
        # enforce integer age and non-negative
        age = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'min': '0', 'step': '1'}))
        gender = forms.ChoiceField(choices=GENDER)
        address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
        # phone stored on model as integer; accept up to 10 digits here and clean to digits-only
        phone_no = forms.CharField(max_length=10,validators=[RegexValidator(r'^\d{1,10}$','Enter up to 10 digits (numbers only).')],widget=forms.TextInput(attrs={'inputmode': 'numeric','maxlength': '10','pattern': r'\d{1,10}',}))

        doctor = forms.ChoiceField(choices=DOCTOR_CHOICES)

        class Meta:
            model = Patient
            fields = ['case', 'name', 'gender', 'age', 'phone_no', 'address', 'doctor']
        
        def clean_phone_no(self):
                raw = self.cleaned_data.get('phone_no', '') or ''
                # remove any non-digit characters just in case
                digits = re.sub(r'\D', '', raw)
                if not digits:
                    raise forms.ValidationError('Enter a phone number with digits only.')
                if len(digits) > 10:
                    raise forms.ValidationError('Phone number must not exceed 10 digits.')
                # convert to int for model's IntegerField (preserve numeric storage)
                try:
                    return int(digits)
                except ValueError:
                    raise forms.ValidationError('Invalid phone number.')


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'generic_name', 'medicine_type', 'manufacturer', 'batch_number', 
                  'expiry_date', 'stock_quantity', 'unit_price', 'reorder_level', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine Name'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Generic Name'}),
            'medicine_type': forms.Select(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Batch Number'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
        }


class SimpleMedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'stock_quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine Name'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }