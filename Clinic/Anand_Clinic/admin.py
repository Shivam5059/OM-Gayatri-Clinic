from django.contrib import admin
from django.utils import timezone
from Anand_Clinic.models import Patient, Medicine
from .models import Profile

# -------------------- PROFILE ADMIN --------------------
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'country_code', 'whatsapp')
    search_fields = ('user__username', 'whatsapp')
    # Make whatsapp editable directly
    list_editable = ('whatsapp',)


# -------------------- PATIENT ADMIN --------------------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('case_no', 'case', 'name', 'age', 'gender', 'phone_no', 'doctor', 'address', 'appointment_date')
    list_filter = ('doctor', 'gender', 'appointment_date')
    # Convert integer phone_no to string search
    search_fields = ('name', 'case', 'case_no', 'phone_no')
    ordering = ('-appointment_date', '-case_no')


# -------------------- MEDICINE ADMIN --------------------
@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'generic_name', 'medicine_type', 'stock_quantity', 'unit_price',
        'expiry_date', 'is_low_stock_display', 'is_expired_display'
    )
    list_filter = ('medicine_type', 'expiry_date')
    search_fields = ('name', 'generic_name', 'manufacturer', 'batch_number')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'is_low_stock_display', 'is_expired_display')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'medicine_type', 'manufacturer', 'description')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'reorder_level', 'batch_number', 'expiry_date',
                       'is_low_stock_display', 'is_expired_display')
        }),
        ('Pricing', {
            'fields': ('unit_price',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # -------------------- SAFE COMPUTED FIELDS --------------------
    def is_low_stock_display(self, obj):
        """Returns True if stock is below reorder level."""
        try:
            return obj.stock_quantity <= obj.reorder_level
        except:
            return False
    is_low_stock_display.boolean = True  # shows as ✔/✖ in admin
    is_low_stock_display.short_description = 'Low Stock'

    def is_expired_display(self, obj):
        """Returns True if medicine is expired."""
        try:
            return obj.expiry_date < timezone.now().date()
        except:
            return False
    is_expired_display.boolean = True
    is_expired_display.short_description = 'Expired'

'''from django.contrib import admin
from Anand_Clinic.models import Patient, Medicine
from .models import Profile

# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'country_code', 'whatsapp')
    search_fields = ('user__username', 'whatsapp')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('case_no', 'case', 'name', 'age', 'gender', 'phone_no', 'doctor', 'address', 'appointment_date')
    list_filter = ('doctor', 'gender', 'appointment_date')
    search_fields = ('name', 'case', 'case_no', 'phone_no')
    ordering = ('-appointment_date', '-case_no',)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'medicine_type', 'stock_quantity', 'unit_price', 'expiry_date', 'is_low_stock', 'is_expired')
    list_filter = ('medicine_type', 'expiry_date')
    search_fields = ('name', 'generic_name', 'manufacturer', 'batch_number')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'is_low_stock', 'is_expired')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'medicine_type', 'manufacturer', 'description')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'reorder_level', 'batch_number', 'expiry_date', 'is_low_stock', 'is_expired')
        }),
        ('Pricing', {
            'fields': ('unit_price',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )'''
