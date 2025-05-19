import base64
import os

import json

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.conf import settings
from django.db.models import F

from pydantic import BaseModel
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from unicodedata import category

from .models import Auction, PhotoSet, Photo, AuctionSet, AuctionParameter, Parameter, AllegroAuthToken, \
    DescriptionTemplate, KeywordTranslation, ParameterTranslation, AuctionParameterTranslation, TranslationExample, \
    Tag, CategoryTag
from django.db.models import Q

from .models.addInventoryProduct import prepare_tags
from django.contrib.auth.models import User, Group
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt

from .models.category_parameter import CategoryParameter
from .serializers.category_parameter import CategoryParameterSerializer
from .serializers.inputtagpreview import InputTagField
from .services import list_directory_contents, AllegroConnector, perform_ocr, put_files_in_completed_directory
from .services.openaiservice import OpenAiService
from .serializers import (
    AuctionSerializer,
    PhotoSetSerializer,
    PhotoSerializer,
    AuctionSetSerializer,
    AuctionParameterSerializer,
    TagSerializer,
    ParameterSerializer,
    DescriptionTemplateSerializer,
    KeywordTranslationSerializer,
    ParameterTranslationSerializer,
    AuctionParameterTranslationSerializer,
    TranslationExampleSerializer, CategoryTagSerializer,
)
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import datetime
from django.shortcuts import redirect, render
import requests

from .services.baselinkerservice import BaseLinkerService
from .services.directorybrowser import put_files_from_auctionset_in_completed_directory, apply_rotation_to_image


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer


class PhotoSetViewSet(viewsets.ModelViewSet):
    queryset = PhotoSet.objects.all()
    serializer_class = PhotoSetSerializer


class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer

class DescriptionTemplateViewSet(viewsets.ModelViewSet):
    queryset = DescriptionTemplate.objects.all()
    serializer_class = DescriptionTemplateSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this endpoint

    def perform_create(self, serializer):
        # Automatically set the owner to the currently logged-in user
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        # Filter the queryset to include only objects owned by the currently authenticated user
        return DescriptionTemplate.objects.filter(owner=self.request.user)

class GetUsersDescriptionTemplates(APIView):
    def get(self, request, user_id):
        templates = DescriptionTemplate.objects.filter(owner=user_id)
        serializer = DescriptionTemplateSerializer(templates, many=True)
        return Response(serializer.data)

class KeywordTranslationViewSet(viewsets.ModelViewSet):
    queryset = KeywordTranslation.objects.all()
    serializer_class = KeywordTranslationSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this endpoint

    def perform_create(self, serializer):
        # Automatically set the owner to the currently logged-in user
        serializer.save(author=self.request.user)

    def get_queryset(self):
        # Filter the queryset to include only objects owned by the currently authenticated user
        return KeywordTranslation.objects.filter(author=self.request.user)

class KeywordTranslationSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Extract the keywords and language from the request data
        keywords = request.data.get('keywords', [])
        language = request.data.get('language', '')
        _category = request.data.get('category', '')

        if not keywords or not language or not _category:
            return Response({"error": "Fields: 'keywords', 'language' and 'category' are required."}, status=400)

        # Convert keywords to lowercase
        keywords = [keyword.lower().strip() for keyword in keywords]

        # Fetch translations for the current user and the specified language
        translations = KeywordTranslation.objects.filter(
            # author=request.user,
            language=language,
            original__in=keywords
        ).filter(
            Q(category=_category) | Q(shared_across_categories=True)
        )

        # Build a dictionary of translations including 'translated' and 'shared_across_categories'
        translations_dict = {
            translation.original: {
                "translated": translation.translated,
                "shared": translation.shared_across_categories,
            }
            for translation in translations
        }

        # Include keywords that have no existing translations
        result = {
            keyword: translations_dict.get(keyword, {"translated": None, "shared": False})
            for keyword in keywords
        }

        return Response(result, status=200)


class GetUsersKeywordTranslation(APIView):
    def get(self, request, user_id):
        templates = KeywordTranslation.objects.filter(author=user_id)
        serializer = KeywordTranslationSerializer(templates, many=True)
        return Response(serializer.data)

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

class DistinctParameterView(APIView):
    """
    Returns a list of distinct Parameter records
    by (allegro_id, name, type).
    Only includes Parameters that have at least one AuctionParameter.
    Note: 'id' will not always match the ID of
    one single row if there are duplicates in those fields,
    but we include it in the dictionary for convenience.
    """

    def get(self, request, *args, **kwargs):
        distinct_params = (
            Parameter.objects
            .filter(auctionparameter__isnull=False)
            .values("id", "allegro_id", "name", "type")
            .distinct()
        )

        return Response(distinct_params, status=status.HTTP_200_OK)

class DistinctAuctionParameterView(APIView):
    """
    Returns a list of distinct AuctionParameter records
    by (parameter, value_name, value_id, auction).
    """
    def get(self, request, *args, **kwargs):
        qs = AuctionParameter.objects.values("parameter", "value_name", "value_id").distinct()
        exploded_results = []
        for item in qs:
            # Split the value_name on '|'
            for part in item["value_name"].split("|"):
                new_item = item.copy()
                new_item["value_name"] = part.strip()  # .strip() if you want to remove extra spaces
                new_item['value_id'] = None
                exploded_results.append(new_item)

        exploded_results = set([tuple(sorted(item.items())) for item in exploded_results])
        exploded_results = [dict(item) for item in exploded_results]

        return Response(exploded_results, status=status.HTTP_200_OK)


class SaveTranslationsView(APIView):
    def post(self, request, *args, **kwargs):
        param_translations = request.data.get("param_translations", [])
        auction_param_translations = request.data.get("auction_param_translations", [])

        # 1) Handle Parameter translations
        for item in param_translations:
            param_id = item.get("param_id")
            translation_text = (item.get("translation") or "").strip()
            if not translation_text:
                continue
            try:
                param_obj = Parameter.objects.get(id=param_id)
                ParameterTranslation.objects.update_or_create(
                    parameter=param_obj,
                    defaults={"translation": translation_text},
                )
            except Parameter.DoesNotExist:
                continue

        # 2) Handle AuctionParameter translations
        for item in auction_param_translations:
            param_id = item.get("param_id")
            value_name = item.get("value_name")
            translation_text = (item.get("translation") or "").strip()
            if not translation_text:
                continue
            try:
                param_obj = Parameter.objects.get(id=param_id)
                auction_param_obj = AuctionParameter.objects.filter(
                    parameter=param_obj,
                    value_name=value_name
                ).first()
                if auction_param_obj:
                    AuctionParameterTranslation.objects.update_or_create(
                        auction_parameter=auction_param_obj,
                        defaults={"translation": translation_text},
                    )
            except Parameter.DoesNotExist:
                continue

        return Response({"message": "Translations saved successfully."}, status=status.HTTP_200_OK)

class ListTranslationsView(APIView):
    def get(self, request, *args, **kwargs):
        param_translations = []
        auction_param_translations = []

        # 1) Parameter translations
        for pt in ParameterTranslation.objects.all():
            param_translations.append({
                "param_id": pt.parameter.id,
                "translation": pt.translation
            })

        # 2) AuctionParameter translations
        for apt in AuctionParameterTranslation.objects.all():
            auction_param_translations.append({
                "param_id": apt.auction_parameter.parameter.id,
                "value_name": apt.auction_parameter.value_name,
                "translation": apt.translation
            })

        return Response({
            "param_translations": param_translations,
            "auction_param_translations": auction_param_translations
        }, status=status.HTTP_200_OK)



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
                {"error": "AuctionSet ID is required"},
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


class TranslateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['title', 'description'],
            properties={
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title for translation'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description for translation'),
            },
        ),
        responses={
            200: openapi.Response(
                description='Translation result',
                examples={
                    'application/json': {
                        'translation': 'Translated text here'
                    }
                }
            ),
            400: 'Bad Request',
            401: 'Unauthorized',
        },
        operation_description="Translate the provided title and description using OpenAI"
    )

    def post(self, request, *args, **kwargs):
        title = request.data.get('title')
        description = request.data.get('description')
        _category = request.data.get('category')

        if not title or not description:
            return Response({"error": "Title and description are required."}, status=status.HTTP_400_BAD_REQUEST)

        openai_service = OpenAiService()
        translation = openai_service.translate_completion(title=title, description=description, category=_category)

        return Response({"translation": translation}, status=status.HTTP_200_OK)

class ImageRotateView(APIView):
    def post(self, request):
        data = request.data
        image_path = data.get('image_path', '')
        angle = data.get('angle', 0)

        if not image_path:
            return Response({'error': 'Image path is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not angle:
            return Response({'error': 'Angle is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Process image path
        # Assuming the image_path format is 'images//<relative_path>'
        if "images/" not in image_path:
            return Response({'error': 'Invalid image path format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract the relative path after 'images//'
        relative_image_path = image_path.split("images//", 1)[1]

        # Normalize the path to prevent directory traversal
        normalized_path = os.path.normpath(relative_image_path)

        if normalized_path.startswith('..') or os.path.isabs(normalized_path):
            return Response({'error': 'Invalid image path.'}, status=status.HTTP_400_BAD_REQUEST)

        # Construct the full file system path
        image_full_path = os.path.join(settings.MEDIA_ROOT, normalized_path)
        print(image_full_path)
        # Check if the file exists
        if not os.path.exists(image_full_path):
            return Response({'error': 'Image file does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        # Rotate the image
        rotated_image_path = apply_rotation_to_image(image_full_path, angle)

        return Response({'rotated_image_path': rotated_image_path}, status=status.HTTP_200_OK)

class TranslationExampleViewSet(viewsets.ModelViewSet):
    queryset = TranslationExample.objects.all().order_by('-created_at')
    serializer_class = TranslationExampleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['source_language', 'target_language', 'category_id']
    search_fields = ['source_text', 'target_text', 'description']


def get_queryset(self):
        queryset = super().get_queryset()
        source_lang = self.request.query_params.get("source_language")
        target_lang = self.request.query_params.get("target_language")

        if source_lang and target_lang:
            queryset = queryset.filter(source_language=source_lang, target_language=target_lang)

        return queryset


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def get_queryset(self):
        language = self.request.query_params.get('language', 'pl')  # Default to Polish
        return Tag.objects.filter(language=language)

    def create(self, request, *args, **kwargs):
        key = request.data.get('key', '').strip()
        value = request.data.get('value', '').strip()
        language = request.data.get('language', 'pl').strip()

        if not key or not value:
            return Response({'error': 'Key and value are required.'}, status=status.HTTP_400_BAD_REQUEST)

        tag, created = Tag.objects.get_or_create(
            key=key, language=language, defaults={'value': value}
        )

        if not created:
            return Response({'error': 'Tag already exists in this language.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        tag_id = kwargs.get('pk')
        language = request.query_params.get('language', 'pl')

        try:
            tag = Tag.objects.get(id=tag_id, language=language)
            tag.value = request.data.get('value', tag.value)
            tag.save()
            return Response(TagSerializer(tag).data)
        except Tag.DoesNotExist:
            return Response({'error': 'Tag not found in this language'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        tag_id = kwargs.get('pk')  # Get the tag ID from the request
        language = request.query_params.get('language', 'pl')  # Default to Polish

        try:
            tag = Tag.objects.get(id=tag_id, language=language)  # Filter by language
            tag.delete()
            return Response({'message': 'Tag deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Tag.DoesNotExist:
            return Response({'error': 'Tag not found in this language'}, status=status.HTTP_404_NOT_FOUND)

class CategoryTagViewSet(viewsets.ModelViewSet):
    queryset = CategoryTag.objects.all()
    serializer_class = CategoryTagSerializer

    def get_queryset(self):
        language = self.request.query_params.get('language', 'pl')  # Default to Polish
        return CategoryTag.objects.filter(language=language)

    def create(self, request, *args, **kwargs):
        category_id = request.data.get('category_id')
        tags = request.data.get('tags', '').strip()
        language = request.data.get('language', 'pl').strip()

        if not category_id or not tags:
            return Response({'error': 'Category ID and tags are required.'}, status=status.HTTP_400_BAD_REQUEST)

        category_tag, created = CategoryTag.objects.get_or_create(
            category_id=category_id, language=language, defaults={'tags': tags}
        )

        if not created:
            return Response({'error': 'Category already exists in this language.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CategoryTagSerializer(category_tag).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        tag_id = kwargs.get('pk')
        language = request.query_params.get('language', 'pl')

        try:
            category_tag = CategoryTag.objects.get(id=tag_id, language=language)
            category_tag.tags = request.data.get('tags', category_tag.tags)
            category_tag.save()
            return Response(CategoryTagSerializer(category_tag).data)
        except CategoryTag.DoesNotExist:
            return Response({'error': 'Category tag not found in this language'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        tag_id = kwargs.get('pk')
        language = request.query_params.get('language', 'pl')

        try:
            category_tag = CategoryTag.objects.get(id=tag_id, language=language)
            category_tag.delete()
            return Response({'message': 'Category tag deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except CategoryTag.DoesNotExist:
            return Response({'error': 'Category tag not found in this language'}, status=status.HTTP_404_NOT_FOUND)

class CategoryParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing custom category parameters with multilingual support.
    Supports listing, retrieving, creating, updating, and deleting.
    Optionally, filtering by category_id can be done by passing a query parameter.
    """
    queryset = CategoryParameter.objects.all()
    serializer_class = CategoryParameterSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category_id')
        if category:
            queryset = queryset.filter(Q(category_id=category) | Q(category_id=None))
        return queryset

class TranslateBaselinkerProductsView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['language', 'product_ids'],
            properties={
                'language': openapi.Schema(type=openapi.TYPE_STRING, description='Target language for translation'),
                'product_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), description='List of product IDs to translate'),
                "inventory_id": openapi.Schema(type=openapi.TYPE_INTEGER, description='Target inventory id for translation')
            },
        ),
        responses={
            200: openapi.Response(
                description='Translation result',
                examples={
                    'application/json': {
                        'translation': 'Translated text here'
                    }
                }
            ),
            400: 'Bad Request',
            401: 'Unauthorized',
        },
        operation_description="Translate Baselinker products using the specified language"
    )

    def post(self, request):
        language = request.data.get('language')
        product_ids = request.data.get('product_ids', [])
        inventory_id = request.data.get('inventory_id')
        if not language or not product_ids:
            return Response({"error": "Language, inventory ID and product IDs are required."}, status=400)

        # Call the translation service
        blservice = BaseLinkerService()
        response = blservice.translate_product_parameters(product_ids, language, inventory_id)

        return Response(response)

class BaselinkerInventoriesView(APIView):
    """
    GET /baselinker/inventories/
    Fetches the list of inventories from BaseLinker and returns only id, name, description.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Fetch all Baselinker inventories",
        responses={
            200: openapi.Response(
                description="A list of inventories",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            ),
            400: 'Bad Request – invalid parameters',
            502: 'Bad Gateway – error communicating with Baselinker',
            500: 'Server configuration error',
        }
    )
    def get(self, request):
        token = getattr(settings, 'BASELINKER_API_TOKEN', None)
        if not token:
            return Response(
                {'error': 'Baselinker API token not configured.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        url = 'https://api.baselinker.com/connector.php'
        headers = {
            'X-BLToken': token,
        }
        payload = {
            'method': 'getInventories',
            'parameters': json.dumps({}),  # must be a JSON-encoded string
        }

        try:
            resp = requests.post(url, headers=headers, data=payload, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            return Response(
                {'error': 'Error communicating with Baselinker API', 'details': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        try:
            bl_data = resp.json()
        except ValueError:
            return Response(
                {'error': 'Invalid JSON from Baselinker', 'content': resp.text},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # BaseLinker itself can return { status: "ERROR", error_message: "...", error_code: ... }
        if bl_data.get('status') == 'ERROR':
            return Response(
                {
                    'error': 'Baselinker returned an error',
                    'message': bl_data.get('error_message'),
                    'code': bl_data.get('error_code'),
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        inventories = bl_data.get('inventories', [])
        simplified = [
            {
                'id': inv.get('inventory_id'),
                'name': inv.get('name'),
                'description': inv.get('description', ''),
            }
            for inv in inventories
        ]

        return Response(simplified, status=status.HTTP_200_OK)