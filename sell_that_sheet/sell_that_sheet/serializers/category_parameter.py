from rest_framework import serializers
from ..models.category_parameter import CategoryParameter

class CategoryParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryParameter
        fields = '__all__'
