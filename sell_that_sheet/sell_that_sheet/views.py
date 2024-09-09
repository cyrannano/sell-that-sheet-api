import os

import json
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Auction, PhotoSet, Photo, AuctionSet, AuctionParameter, Parameter
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
        print(authorization_url)

        # make a get request to the authorization_url
        return redirect(authorization_url)


class AllegroCallbackView(APIView):
    def get(self, request):
        connector = AllegroConnector()
        token = connector.fetch_token(request.build_absolute_uri())
        os.environ["allegro_token"] = json.dumps(token)
        # Store the token securely (e.g., in the session or database)
        return Response(
            {"message": "Token fetched successfully"}, status=status.HTTP_200_OK
        )


class AllegroGetCategoryParametersView(APIView):
    def get(self, request, categoryId):
        connector = AllegroConnector()
        url = f"https://api.allegro.pl/sale/categories/{categoryId}/parameters"
        response = connector.make_authenticated_get_request(request, url)
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
