from rest_framework import serializers

from ..models import DescriptionTemplate


class DescriptionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DescriptionTemplate
        fields = '__all__'
        read_only_fields = ['owner']
