from rest_framework import serializers
from ..models import CategoryTag

class CategoryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryTag
        fields = ['id', 'category_id', 'tags', 'language']
