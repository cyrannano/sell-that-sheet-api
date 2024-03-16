from django.db import models
from .auction import Auction


class AuctionSet(models.Model):
    auctions = models.ManyToManyField(Auction, related_name='auctionsets')
    directory_location = models.CharField(max_length=255)

    def __str__(self):
        return f"AuctionSet {self.id}"