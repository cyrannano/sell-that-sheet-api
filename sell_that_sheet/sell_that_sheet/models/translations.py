from django.db import models
from .parameter import Parameter, AuctionParameter

class ParameterTranslation(models.Model):
    """
    Stores a translation for a given Parameter.
    """
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    translation = models.CharField(max_length=255)

    def __str__(self):
        return f"Translation for {self.parameter.name} -> {self.translation}"


class AuctionParameterTranslation(models.Model):
    """
    Stores a translation for a given AuctionParameter value.
    """
    auction_parameter = models.ForeignKey(AuctionParameter, on_delete=models.CASCADE)
    translation = models.CharField(max_length=255)

    def __str__(self):
        return f"Translation for {self.auction_parameter.value_name} -> {self.translation}"
