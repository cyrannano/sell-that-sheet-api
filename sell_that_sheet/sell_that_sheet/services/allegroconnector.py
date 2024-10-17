from requests_oauthlib import OAuth2Session
from django.conf import settings
import requests
import os
import json
from ..models import AllegroAuthToken
from django.utils import timezone
from datetime import timedelta


CLIENT_ID = settings.ALLEGRO_CLIENT_ID
CLIENT_SECRET = settings.ALLEGRO_CLIENT_SECRET
REDIRECT_URI = settings.ALLEGRO_REDIRECT_URI
AUTHORIZATION_BASE_URL = settings.ALLEGRO_AUTHORIZATION_BASE_URL
TOKEN_URL = settings.ALLEGRO_TOKEN_URL
SCOPES = settings.ALLEGRO_SCOPES
STATE = settings.ALLEGRO_STATE


class AllegroConnector:
    def __init__(self):
        self.oauth = OAuth2Session(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES, state=STATE)

    def get_authorization_url(self):
        # Redirect the user to the OAuth2 provider's authorization page
        authorization_url, _ = self.oauth.authorization_url(AUTHORIZATION_BASE_URL)
        return authorization_url

    def fetch_token(self, authorization_response):
        # Fetch the access token using the authorization response URL
        token = self.oauth.fetch_token(TOKEN_URL, authorization_response=authorization_response,
                                       client_secret=CLIENT_SECRET, verify=False)
        return token

    def refresh_token(self, refresh_token):
        # Refresh the access token
        extra = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
        new_token = self.oauth.refresh_token(TOKEN_URL, refresh_token=refresh_token, **extra)
        return new_token

    def get_allegro_access_token(self):
        # Get the allegro auth token from the database
        token = AllegroAuthToken.objects.first()
        if token:
            # Check if the token is expired
            if token.expires_at < timezone.now():
                # Refresh the token
                new_token = self.refresh_token(token.refresh_token)
                token.access_token = new_token['access_token']
                token.refresh_token = new_token['refresh_token']
                token.expires_at = timezone.now() + timedelta(seconds=new_token['expires_in'])
                token.save()
            return token.access_token
        return None

    def get_category_tree(self, cat_id):
        url = 'https://api.allegro.pl' + f'/sale/categories/{cat_id}'
        return self.make_authenticated_get_request('get_category_tree', url)


    def make_authenticated_get_request(self, request, url, params=None):
        # Assuming the token is stored in the session for this example
        access_token = self.get_allegro_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.allegro.public.v1+json'
                   }
        response = requests.get(url, headers=headers, params=params)
        return response.json()