from ..models import Parameter, AuctionParameter
from rest_framework import serializers


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ['id', 'allegro_id', 'name', 'type']


class AuctionParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionParameter
        fields = ['parameter', 'value_name', 'value_id', 'auction']

