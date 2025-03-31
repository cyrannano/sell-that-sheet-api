from django.db import models

class CategoryTag(models.Model):
    category_id = models.IntegerField()
    tags = models.TextField()  # Store multiple tags as text
    language = models.CharField(max_length=2, choices=[('pl', 'Polish'), ('de', 'German')])

    class Meta:
        unique_together = ('category_id', 'language')  # Ensure unique category per language

    def __str__(self):
        return f"Category {self.category_id} ({self.language})"
