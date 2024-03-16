from rest_framework import viewsets
from .models import Auction, PhotoSet, Photo, AuctionSet, AuctionParameter, Parameter
from .serializers import AuctionSerializer, PhotoSetSerializer, PhotoSerializer, AuctionSetSerializer, AuctionParameterSerializer, ParameterSerializer


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer


class PhotoSetViewSet(viewsets.ModelViewSet):
    queryset = PhotoSet.objects.all()
    serializer_class = PhotoSetSerializer


class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer


class AuctionSetViewSet(viewsets.ModelViewSet):
    queryset = AuctionSet.objects.all()
    serializer_class = AuctionSetSerializer


class AuctionParameterViewSet(viewsets.ModelViewSet):
    queryset = AuctionParameter.objects.all()
    serializer_class = AuctionParameterSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer



