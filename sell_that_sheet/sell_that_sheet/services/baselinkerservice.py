import os
import logging
import requests
import json
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from django.conf import settings

from .utils import prepare_temp_directory, remove_temp_directory
from ..models import AddInventoryProduct, AddInventoryProductResponse
from .allegroconnector import AllegroConnector

from ..models import AuctionSet

logger = logging.getLogger(__name__)

class BaseLinkerService:
    BASE_URL = "https://api.baselinker.com/connector.php"
    BASE_HEADER = {
        "X-BLToken": settings.BASELINKER_API_KEY,
    }


    def __init__(self):
        self.categories = self.get_categories()
        self.manufacturers = self.get_manufacturers()

    def _post(self, method: str, data: Optional[Dict] = None) -> Dict:
        payload = {
            "method": method,
            "parameters": json.dumps(data or {}) if not isinstance(data, str) else data,
        }
        logger.debug(f"Sending POST request to {self.BASE_URL} with payload: {payload}")
        try:
            response = requests.post(url=self.BASE_URL, headers=self.BASE_HEADER, data=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error during BaseLinker API request: {e}")
            raise

    def get_categories(self) -> List[Dict]:
        try:
            logger.info("Fetching categories from BaseLinker")
            response = self._post("getInventoryCategories")
            return response.get('categories', [])
        except Exception as e:
            logger.error("Failed to fetch categories", exc_info=e)
            return []

    def create_category(self, name: str) -> int:
        logger.info(f"Creating new category: {name}")
        try:
            response = self._post("addInventoryCategory", {"name": name, "parent_id": 0})
            new_category_id = int(response['category_id'])
            # Refresh categories after creation
            self.categories = self.get_categories()
            return new_category_id
        except Exception as e:
            logger.error(f"Failed to create category {name}", exc_info=e)
            raise

    def match_category(self, category) -> int:
        connector = AllegroConnector()
        tree = connector.get_category_tree(category)
        logger.info(f"Matching category for tree: {tree}")
        for category in self.categories:
            if category['name'] == tree:
                return category['category_id']
        # If not found, create a new category
        print(f"Creating new category: {tree}")
        return self.create_category(tree)

    def get_manufacturers(self) -> List[Dict]:
        try:
            logger.info("Fetching manufacturers from BaseLinker")
            response = self._post("getInventoryManufacturers")
            return response.get('manufacturers', [])
        except Exception as e:
            logger.error("Failed to fetch manufacturers", exc_info=e)
            return []

    def match_manufacturer(self, name: str) -> Optional[int]:
        logger.info(f"Matching manufacturer for: {name}")
        original_name = name
        name = name.lower()
        max_distance = 0.9
        matched_id = None

        for manufacturer in self.manufacturers:
            if manufacturer['name'].lower() == name:
                return manufacturer['manufacturer_id']
            distance = SequenceMatcher(None, name, manufacturer['name'].lower()).ratio()
            if distance > max_distance:
                max_distance = distance
                matched_id = manufacturer['manufacturer_id']

        if not matched_id:
            matched_id = self.create_manufacturer(original_name)
        return matched_id

    def create_manufacturer(self, name: str) -> int:
        logger.info(f"Creating new manufacturer: {name}")
        try:
            response = self._post("addInventoryManufacturer", {"name": name})
            new_manufacturer_id = int(response['manufacturer_id'])
            # Refresh manufacturers after creation
            self.manufacturers = self.get_manufacturers()
            return new_manufacturer_id
        except Exception as e:
            logger.error(f"Failed to create manufacturer {name}", exc_info=e)
            raise

    def upload_product(self, product: AddInventoryProduct) -> AddInventoryProductResponse:
        logger.info(f"Uploading product: {product.sku}")
        try:
            product_data = product.model_dump_json()
            response = self._post("addInventoryProduct", product_data)
            return AddInventoryProductResponse(**response)
        except Exception as e:
            logger.error(f"Failed to upload product {product.sku}", exc_info=e)
            raise

    def prepare_products(self, auctionset: AuctionSet) -> List[AddInventoryProduct]:
        products = []
        tmp_dir = prepare_temp_directory()
        for auction in auctionset.auctions.all():
            product = AddInventoryProduct.from_auction(auction=auction, inventory_id=1430, match_manufacturer=self.match_manufacturer, match_category=self.match_category, owner=auctionset.owner, author=auctionset.creator)
            products.append(product)
        remove_temp_directory(tmp_dir)
        return products

    def upload_products(self, auctionset: AuctionSet) -> List[AddInventoryProductResponse]:
        products = self.prepare_products(auctionset)
        responses = []
        for product in products:
            response = self.upload_product(product)
            responses.append(response)
        return responses
