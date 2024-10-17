from django.db import models
from .auction import Auction
from django.contrib.auth.models import User

class AuctionSet(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    auctions = models.ManyToManyField(Auction, related_name='auctionsets')
    directory_location = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_auctionsets')
    owner = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AuctionSet {self.id}"