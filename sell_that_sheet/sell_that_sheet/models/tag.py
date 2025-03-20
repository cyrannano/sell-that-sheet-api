from django.db import models

class Tag(models.Model):
    key = models.CharField(max_length=255)
    value = models.TextField()
    language = models.CharField(max_length=2, choices=[('pl', 'Polish'), ('de', 'German')])

    class Meta:
        unique_together = ('key', 'language')  # Ensure unique keys per language

    def __str__(self):
        return f"{self.key} ({self.language})"
