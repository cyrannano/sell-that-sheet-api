from rest_framework import serializers
from ..models import TranslationExample

class TranslationExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationExample
        fields = '__all__'
