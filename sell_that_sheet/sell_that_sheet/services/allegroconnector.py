from requests_oauthlib import OAuth2Session
from django.conf import settings
import requests
import os
import json
from ..models import AllegroAuthToken
from django.utils import timezone
from datetime import timedelta
from openpyxl import Workbook


CLIENT_ID = settings.ALLEGRO_CLIENT_ID
CLIENT_SECRET = settings.ALLEGRO_CLIENT_SECRET
REDIRECT_URI = settings.ALLEGRO_REDIRECT_URI
AUTHORIZATION_BASE_URL = settings.ALLEGRO_AUTHORIZATION_BASE_URL
TOKEN_URL = settings.ALLEGRO_TOKEN_URL
SCOPES = settings.ALLEGRO_SCOPES
STATE = settings.ALLEGRO_STATE


class AllegroConnector:
    BASE_URL = "https://api.allegro.pl"

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
        # Base URL for the API endpoint
        url = f"https://api.allegro.pl/sale/categories/{cat_id}"

        # Fetch category data
        category_data = self.make_authenticated_get_request('get_category_tree', url)

        # Extract name and parent
        category_name = category_data.get("name", "")
        parent_category = category_data.get("parent")

        # If there's a parent, recursively get its category tree
        if parent_category:
            parent_id = parent_category.get("id")
            if parent_id:  # Ensure parent ID is not None
                return f"{self.get_category_tree(parent_id)}/{category_name}"

        # If there's no parent, return the current category name
        return category_name

    def make_authenticated_get_request(self, request, url, params=None):
        # Assuming the token is stored in the session for this example
        access_token = self.get_allegro_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.allegro.public.v1+json'
                   }
        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def fetch_all_offers(self, limit: int = 100) -> list:
        """
        Retrieve all seller offers by paginating through the /sale/offers endpoint.
        """
        offers = []
        offset = 0
        while True:
            params = {"limit": limit, "offset": offset}
            response = self.make_authenticated_get_request(
                None,
                f"{self.BASE_URL}/sale/offers",
                params=params
            )
            batch = response.get("offers", [])
            if not batch:
                break
            offers.extend(batch)
            offset += limit
        return offers

    def fetch_offer_details(self, offer_id: str) -> dict:
        """
        Retrieve detailed data for a single offer, including its product parameters.
        """
        return self.make_authenticated_get_request(
            None,
            f"{self.BASE_URL}/sale/product-offers/{offer_id}"
        )

    def download_catalogue(self) -> list:
        """
        Download the full catalogue of offers with human-readable parameter names and values.
        """
        all_offers = self.fetch_all_offers()
        detailed_offers = []
        for offer in all_offers:
            offer_id = offer["id"]
            full = self.fetch_offer_details(offer_id)
            # Extract and map parameters by name → first value’s 'value'
            params = {}
            for p in full.get("product", {}).get("parameters", []):
                name = p.get("name")
                values = p.get("values", [])
                # Use the first available value; adjust if multiple
                val_name = values[0].get("value") if values else None
                params[name] = val_name
            full["parameters_dict"] = params
            detailed_offers.append(full)
        return detailed_offers

def export_catalogue_to_xlsx(catalogue: list, filename: str = "catalogue.xlsx"):
    """
    Export the catalogue (list of offers with parameters_dict) to an XLSX file.
    """
    wb = Workbook()
    ws = wb.active

    # Determine all unique parameter names for headers
    param_keys = set()
    for item in catalogue:
        param_keys.update(item["parameters_dict"].keys())
    headers = ["offerId", "offerName"] + sorted(param_keys)
    ws.append(headers)

    for item in catalogue:
        offer_id = item.get("id")
        name = item.get("name")
        row = [offer_id, name]
        params = item["parameters_dict"]
        row.extend(params.get(k, "") for k in sorted(param_keys))
        ws.append(row)

    wb.save(filename)
