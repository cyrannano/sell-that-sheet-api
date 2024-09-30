import os

import json
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Auction, PhotoSet, Photo, AuctionSet, AuctionParameter, Parameter, AllegroAuthToken
from .services import list_directory_contents, AllegroConnector
from .serializers import (
    AuctionSerializer,
    PhotoSetSerializer,
    PhotoSerializer,
    AuctionSetSerializer,
    AuctionParameterSerializer,
    ParameterSerializer,
)
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import datetime
from django.shortcuts import redirect, render
import requests


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

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class AuctionParameterViewSet(viewsets.ModelViewSet):
    queryset = AuctionParameter.objects.all()
    serializer_class = AuctionParameterSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class DirectoryBrowseView(APIView):
    def get(self, request, path=None):
        try:
            contents = list_directory_contents(path)
            return Response(contents)
        except FileNotFoundError:
            return Response(
                {"error": "The specified path does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "userData": {
                        "userName": user.get_short_name(),
                        "userLogin": user.get_username(),
                    },
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        return Response(
            {"message": "Successfully logged out."}, status=status.HTTP_200_OK
        )


class AllegroLoginView(APIView):
    """
    This view initiates the Allegro OAuth2 authorization process.
    It's not compliant with OAuth2 standard, because of some limitations of my client's network
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        connector = AllegroConnector()
        authorization_url = connector.get_authorization_url()

        return Response({"authorization_url": authorization_url})


class AllegroCallbackView(APIView):
    def get(self, request):
        connector = AllegroConnector()
        token = connector.fetch_token(request.build_absolute_uri())
        # os.environ["allegro_token"] = json.dumps(token)
        # Store the token securely (e.g., in the session or database)
        AllegroAuthToken.objects.all().delete()
        AllegroAuthToken.objects.create(
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            expires_at=timezone.make_aware(datetime.datetime.fromtimestamp(token["expires_at"])),
        )
        return Response(
            {"message": "Token fetched successfully"}, status=status.HTTP_200_OK
        )

def check_new_parameters(parameters):
    for parameter in parameters:
        try:
            Parameter.objects.get(allegro_id=parameter["id"])
        except Parameter.DoesNotExist:
            Parameter.objects.create(allegro_id=parameter["id"], name=parameter["name"], type=parameter["type"])

class AllegroGetCategoryParametersView(APIView):
    def get(self, request, categoryId):
        connector = AllegroConnector()
        url = f"https://api.allegro.pl/sale/categories/{categoryId}/parameters"
        response = connector.make_authenticated_get_request(request, url)
        # async check if response parameters are already in the database and if not, save them
        check_new_parameters(response['parameters'])
        return Response(response)


class AllegroMatchCategoryView(APIView):
    def get(self, request, name):

        connector = AllegroConnector()
        url = f"https://api.allegro.pl/sale/matching-categories/"
        params = {"name": name}
        response = connector.make_authenticated_get_request(request, url, params)
        return Response(response)


class AllegroGetCategoryByIdView(APIView):
    def get(self, request, categoryId):
        connector = AllegroConnector()
        url = f"https://api.allegro.pl/sale/categories/{categoryId}"
        response = connector.make_authenticated_get_request(request, url)
        return Response(response)


from django.http import JsonResponse
from django.apps import apps


class GetModelStructure(APIView):
    def get(self, request, app_label, model_name):
        try:
            model = apps.get_model(app_label, model_name)
            model_structure = []

            for field in model._meta.get_fields():
                try:
                    field_info = {
                        "name": field.name,
                        "type": field.get_internal_type(),
                        "null": field.null if hasattr(field, "null") else None,
                        "primary_key": field.primary_key,
                    }
                    model_structure.append(field_info)
                except AttributeError:
                    pass

            return JsonResponse({"model": model_name, "structure": model_structure})

        except LookupError:
            return JsonResponse({"error": "Model not found"}, status=404)

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from openpyxl import Workbook
from io import BytesIO

from .models import AuctionSet, Auction, AuctionParameter, Parameter

def download_auctionset_xlsx(request, auctionset_id):
    # Get the AuctionSet object
    auctionset = get_object_or_404(AuctionSet, pk=auctionset_id)

    # Create an in-memory output file for the workbook.
    output = BytesIO()

    # Create a workbook and add a worksheet.
    wb = Workbook()
    ws = wb.active
    ws.title = f"AuctionSet {auctionset.id}"

    # Prepare headers
    headers = [
        'Nazwa',        # Auction name
        'Cena',         # Price in PLN
        'Cena Euro',    # Price in Euro
        'Wysyłka',      # Shipping price
        'Nr części',    # Part number (serial_numbers)
        'Tagi',         # Tags
        'Opis',         # Description
        'Kategoria',    # Category
        'Producent',    # Manufacturer (from parameters)
        'Pierwsze zdjęcie'  # Thumbnail image path
    ]

    # Collect all unique parameter names used in the auctions
    parameter_names = set()
    for auction in auctionset.auctions.all():
        auction_parameters = AuctionParameter.objects.filter(auction=auction)
        for ap in auction_parameters:
            parameter_names.add(ap.parameter.name)

    parameter_names = list(parameter_names)
    headers.extend(parameter_names)

    # Write headers to the worksheet
    ws.append(headers)

    # Write data for each auction
    for auction in auctionset.auctions.all():
        row = [
            auction.name,
            auction.price_pln,
            auction.price_euro,
            auction.shipment_price,
            auction.serial_numbers,
            auction.tags,
            auction.description,
            auction.category,
            '',  # Placeholder for Producent
            ''   # Placeholder for Pierwsze zdjęcie
        ]

        # Get 'Producent' from parameters if it exists
        producent_value = ''
        producent_param = AuctionParameter.objects.filter(
            auction=auction,
            parameter__name='Producent'
        ).first()
        if producent_param:
            producent_value = producent_param.value_name
        row[8] = producent_value  # Set Producent value

        # Get the thumbnail image path
        pierwsze_zdjecie = ''
        if auction.photoset and auction.photoset.thumbnail:
            pierwsze_zdjecie = auction.photoset.thumbnail.name
        row[9] = pierwsze_zdjecie  # Set Pierwsze zdjęcie value

        # Create a dictionary of parameters for quick access
        auction_parameters = AuctionParameter.objects.filter(auction=auction)
        param_dict = {ap.parameter.name: ap.value_name for ap in auction_parameters}

        # Add parameter values to the row
        for param_name in parameter_names:
            row.append(param_dict.get(param_name, ''))

        # Append the row to the worksheet
        ws.append(row)

    # Save the workbook to the in-memory output file
    wb.save(output)
    output.seek(0)

    # Set up the HttpResponse with the appropriate headers
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=AuctionSet_{auctionset.id}.xlsx'

    return response
