from rest_framework import serializers
from ..models import AuctionSet


class AuctionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionSet
        fields = '__all__'
