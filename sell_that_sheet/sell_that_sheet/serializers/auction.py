from rest_framework import serializers
from ..models import Auction


class AuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ['id', 'name', 'price_pln', 'price_euro', 'tags', 'serial_numbers', 'photoset', 'shipment_price', 'description', 'category', 'created_at', 'amount', 'translated_params']
        read_only_fields = ('created_at', 'id')

    price_euro = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    tags = serializers.CharField(allow_null=True, allow_blank=True)
    serial_numbers = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    description = serializers.CharField(allow_null=True, allow_blank=True)
