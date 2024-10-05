from rest_framework import serializers
from ..models import AuctionSet


class AuctionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionSet
        fields = '__all__'
        read_only_fields = ('creator', 'created_at')

    creator = serializers.SlugRelatedField(read_only=True, slug_field='username')


