from rest_framework import serializers

from ..models import KeywordTranslation


class KeywordTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordTranslation
        fields = '__all__'
        read_only_fields = ('created_at', 'id', 'author')
