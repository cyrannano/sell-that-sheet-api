from django.db import models

# Model for Custom Category Parameters with multilingual support
class CategoryParameter(models.Model):
    category_id = models.CharField(max_length=255, verbose_name="ID kategorii", null=True)
    name_pl = models.CharField(max_length=255, verbose_name="Nazwa (PL)")
    name_de = models.CharField(max_length=255, verbose_name="Nazwa (DE)")
    separator = models.CharField(max_length=10, default=";", verbose_name="Separator")

    parameter_type = models.CharField(
        max_length=20,
        choices=(
            ('single', 'Lista (jednokrotny wybór)'),
            ('multi', 'Checkbox (wielokrotny wybór)'),
            ('numeric', 'Liczbowy'),
            ('text', 'Tekstowy')
        ),
        verbose_name="Typ parametru"
    )
    possible_values_pl = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Możliwe wartości (PL)",
        help_text="Przechowuje listę wartości w języku polskim, jeśli dotyczy."
    )
    possible_values_de = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Możliwe wartości (DE)",
        help_text="Przechowuje listę wartości w języku niemieckim, jeśli dotyczy."
    )

    def __str__(self):
        return f"{self.category_id} - {self.name_pl}"
