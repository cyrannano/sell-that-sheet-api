from django.db import models

class AllegroAuthToken(models.Model):
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"AllegroAuthToken {self.id}"
