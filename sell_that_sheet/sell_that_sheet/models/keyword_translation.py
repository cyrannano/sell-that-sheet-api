from django.conf import settings
from django.db import models


class KeywordTranslation(models.Model):
    original = models.CharField(max_length=255)
    translated = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    language = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=15)
    shared_across_categories = models.BooleanField(default=False)
