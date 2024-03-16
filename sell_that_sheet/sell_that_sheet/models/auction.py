from django.db import models
from .photoset import PhotoSet


class Auction(models.Model):
    name = models.CharField(max_length=255)
    price_pln = models.DecimalField(max_digits=10, decimal_places=2)
    price_euro = models.DecimalField(max_digits=10, decimal_places=2)
    tags = models.CharField(max_length=255)
    serial_numbers = models.CharField(max_length=255)
    photoset = models.ForeignKey(PhotoSet, on_delete=models.CASCADE)

    def __str__(self):
        return self.name