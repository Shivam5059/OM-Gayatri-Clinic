from django.apps import AppConfig

class AnandClinicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Anand_Clinic"

    def ready(self):
        import Anand_Clinic.signal

class PatientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Anand_Clinic'
