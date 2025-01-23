from rest_framework import serializers
from ..models.translations import ParameterTranslation, AuctionParameterTranslation

class ParameterTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterTranslation
        fields = '__all__'


class AuctionParameterTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionParameterTranslation
        fields = '__all__'
