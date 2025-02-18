from django.db import models

class TranslationExample(models.Model):
    source_language = models.CharField(max_length=10)  # e.g., "pl" for Polish
    target_language = models.CharField(max_length=10)  # e.g., "de" for German
    source_text = models.TextField()
    target_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source_language', 'target_language', 'source_text')

    def __str__(self):
        return f"[{self.source_language} → {self.target_language}] {self.source_text} - {self.target_text}"
