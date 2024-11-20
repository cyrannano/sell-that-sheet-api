from django.conf import settings
from django.db import models
from .auction import Auction


class AuctionSet(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    auctions = models.ManyToManyField(Auction, related_name='auctionsets')
    directory_location = models.CharField(max_length=255)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_auctionsets')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_auctionsets')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AuctionSet {self.id}"