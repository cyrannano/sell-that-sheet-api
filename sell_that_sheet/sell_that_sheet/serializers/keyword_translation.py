from rest_framework import serializers

from ..models import KeywordTranslation


class KeywordTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordTranslation
        fields = '__all__'
        read_only_fields = ('created_at', 'id', 'author')

        # Convert 'original' and 'translation' fields to lowercase
        def to_internal_value(self, data):
            data['original'] = data['original'].lower()
            data['translation'] = data['translation'].lower()
            return super().to_internal_value(data)