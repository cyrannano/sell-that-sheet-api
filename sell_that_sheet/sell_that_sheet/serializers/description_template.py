from rest_framework import serializers

from ..models import DescriptionTemplate


class DescriptionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DescriptionTemplate
        fields = '__all__'
