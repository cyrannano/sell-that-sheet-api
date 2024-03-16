from rest_framework import viewsets
from .models import Auction
from .serializers import AuctionSerializer


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
