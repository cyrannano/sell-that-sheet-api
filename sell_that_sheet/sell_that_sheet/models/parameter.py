from django.db import models
from .auction import Auction


class Parameter(models.Model):
    allegro_id = models.CharField(max_length=255, verbose_name="Allegro parameter ID")
    name = models.CharField(max_length=255, verbose_name="Parameter name")
    type = models.CharField(max_length=255, verbose_name="Parameter type")


class AuctionParameter(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, verbose_name="Associated Parameter")
    value_name = models.CharField(max_length=255, verbose_name="Parameter Value name")
    value_id = models.CharField(max_length=35, verbose_name="Parameter Value id")
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, verbose_name="Associated Auction")
