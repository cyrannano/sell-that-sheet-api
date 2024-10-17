from django.db import models
from .photoset import PhotoSet


class Auction(models.Model):
    name = models.CharField(max_length=255)
    price_pln = models.DecimalField(max_digits=10, decimal_places=2)
    price_euro = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    tags = models.CharField(max_length=255, null=True)
    serial_numbers = models.CharField(max_length=255, null=True)
    photoset = models.ForeignKey(PhotoSet, on_delete=models.CASCADE)
    shipment_price = models.IntegerField(null=True)
    description = models.TextField(null=True)
    category = models.CharField(max_length=15, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField(default=1)

    def __str__(self):
        return self.name
