from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser  # Replace with your custom user model's name

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Adding 'star_id' to the admin fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('star_id',),  # Add your custom field here
            'description': 'Value of star_id for Baselinker (1-5)',
        }),
    )
