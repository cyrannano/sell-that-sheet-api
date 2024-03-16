from rest_framework import serializers
from ..models import PhotoSet


class PhotoSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoSet
        fields = '__all__'
