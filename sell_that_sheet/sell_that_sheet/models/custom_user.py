from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    star_id = models.IntegerField(null=True, blank=True, help_text="Value of star_id for Baselinker (1-5)")