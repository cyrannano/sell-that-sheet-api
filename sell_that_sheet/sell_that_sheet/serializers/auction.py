from rest_framework import serializers
from ..models import Auction


class AuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ['id', 'name', 'price_pln', 'price_euro', 'tags', 'serial_numbers', 'photoset']