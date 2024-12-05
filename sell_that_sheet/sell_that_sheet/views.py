import base64
import os

import json

from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from pydantic import BaseModel
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Auction, PhotoSet, Photo, AuctionSet, AuctionParameter, Parameter, AllegroAuthToken
from .models.addInventoryProduct import prepare_tags
from django.contrib.auth.models import User, Group
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt

from .serializers.inputtagpreview import InputTagField
from .services import list_directory_contents, AllegroConnector, perform_ocr, put_files_in_completed_directory
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

from .services.baselinkerservice import BaseLinkerService
from .services.directorybrowser import put_files_from_auctionset_in_completed_directory


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
        # Get the creator (current user)
        creator = self.request.user

        # Check if the creator belongs to the "owners" group
        owners_group = Group.objects.filter(name="owners").first()
        is_creator_owner = owners_group and creator in owners_group.user_set.all()

        # Check if the owner is explicitly set in the request
        owner = serializer.validated_data.get('owner')

        if owner is None:
            if is_creator_owner:
                # Automatically set owner to the creator if they are in the "owners" group
                owner = creator
            else:
                # Raise an error if the creator is not in the "owners" group
                raise ValidationError({"detail": "Nie podano właściciela pakietu"})

        # Save the instance with the appropriate owner and creator
        serializer.save(creator=creator, owner=owner)


class AuctionParameterViewSet(viewsets.ModelViewSet):
    queryset = AuctionParameter.objects.all()
    serializer_class = AuctionParameterSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    filter_backends = [DjangoFilterBackend]
    serializer_class = ParameterSerializer
    filterset_fields = ["allegro_id"]


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


class CompleteFilesView(APIView):
    """
    API view to mark an auction's files as complete by moving them
    to a completed directory.
    """

    def get(self, request, auction_id=None, *args, **kwargs):
        if not auction_id:
            return Response(
                {"error": "Auction ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrieve the auction instance
        auction = get_object_or_404(Auction, id=auction_id)

        try:
            completed_dir = put_files_in_completed_directory(auction)
            return Response(
                {
                    "message": "Files moved successfully",
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print the exception stack trace (replace with proper logging in production)
            print(e)
            return Response({"error": "Unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CompleteAuctionSetFilesView(APIView):
    """
    API view to mark an auction's files as complete by moving them
    to a completed directory.
    """

    def get(self, request, auction_set_id=None, *args, **kwargs):
        if not auction_set_id:
            return Response(
                {"error": "Auction ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrieve the auctionset instance
        auction_set = get_object_or_404(AuctionSet, id=auction_set_id)

        try:
            completed_dir = put_files_from_auctionset_in_completed_directory(auction_set)
            return Response(
                {
                    "message": "Files moved successfully",
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print the exception stack trace (replace with proper logging in production)
            print(e)
            return Response({"error": "Unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

class UserView(APIView):
    """
    This view returns user data
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id:
            user = User.objects.get(pk=user_id)
            return Response(
                {
                    "userData": {
                        "userName": user.get_short_name(),
                        "userLogin": user.get_username(),
                    }
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "userData": {
                    "userName": request.user.get_short_name(),
                    "userLogin": request.user.get_username(),
                }
            },
            status=status.HTTP_200_OK,
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

class UploadAuctionSetToBaselinkerView(APIView):
    def post(self, request, auctionset_id):
        auctionset = AuctionSet.objects.get(pk=auctionset_id)
        baselinker_service = BaseLinkerService()
        response = baselinker_service.upload_products(auctionset)
        return Response(response)



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

class PrepareTagFieldPreview(APIView):
    @swagger_auto_schema(
        request_body=InputTagField,
        responses={200: 'Success'},
        operation_description="Preview tags based on the input data"
    )
    def post(self, request, *args, **kwargs):
        serializer = InputTagField(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        categoryId = serializer.validated_data['categoryId']
        auctionName = serializer.validated_data['auctionName']
        auctionTags = serializer.validated_data['auctionTags']

        response = prepare_tags(categoryId, auctionName, auctionTags)
        return Response(response)

class PerformOcrView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['image_path'],
            properties={
                'image_path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to the image file to be processed. Images larger than 1MB will be automatically resized.'
                ),
            },
        ),
        responses={
            200: 'Success',
            400: 'Bad Request',
            500: 'Internal Server Error',
        },
        operation_description="Perform OCR on the provided image file. Images larger than 1MB will be automatically resized."
    )
    def post(self, request):
        try:
            data = request.data
            image_path = data.get('image_path', '')

            # Validate the image_path
            if not image_path:
                return Response(
                    {'error': 'Image path is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process image path
            # Assuming the image_path format is 'images//<relative_path>'
            if "images//" not in image_path:
                return Response(
                    {'error': 'Invalid image path format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract the relative path after 'images//'
            relative_image_path = image_path.split("images//", 1)[1]

            # Normalize the path to prevent directory traversal
            normalized_path = os.path.normpath(relative_image_path)

            if normalized_path.startswith('..') or os.path.isabs(normalized_path):
                return Response(
                    {'error': 'Invalid image path.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Construct the full file system path
            image_full_path = os.path.join(settings.MEDIA_ROOT, normalized_path)

            # Check if the file exists
            if not os.path.exists(image_full_path):
                return Response(
                    {'error': 'Image file does not exist.'},
                    status=status.HTTP_400_BAD_REQUEST
                )


            # Perform OCR on the image
            parsed_text = perform_ocr(image_full_path)

            return Response({'parsed_text': parsed_text}, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            # Log the exception (replace with proper logging in production)
            print('Error communicating with OCR API:', e)
            return Response(
                {'error': 'Failed to communicate with the OCR API.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            # Log the exception (replace with proper logging in production)
            print('Error performing OCR:', e)
            return Response(
                {'error': 'An error occurred during OCR processing.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ListGroupUsersView(APIView):
    def get(self, request, group_name):
        try:
            group = Group.objects.get(name=group_name)
            users = group.user_set.all()
            user_data = [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                }
                for user in users
            ]
        except Group.DoesNotExist:
            return Response(
                {'error': f'Group {group_name} does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(user_data)