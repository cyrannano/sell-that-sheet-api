from rest_framework import serializers

class InputTagField(serializers.Serializer):
    categoryId = serializers.IntegerField(required=True)
    auctionName = serializers.CharField(required=True)
    auctionTags = serializers.CharField(required=False, allow_null=True, allow_blank=True)