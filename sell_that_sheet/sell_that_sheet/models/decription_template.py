from django.conf import settings
from django.db import models


class DescriptionTemplate(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

