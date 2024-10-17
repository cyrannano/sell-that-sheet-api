from django.db import models
import os
from typing import Dict, Optional, List, Union
from .parameter import AuctionParameter
from django.conf import settings
from ..services.utils import parse_photos, limit_photo_size
from pydantic import BaseModel


def map_shipment_to_weight(shipment):
    return settings.SHIPMENT_WEIGHT_MAPPING[int(float(shipment))]

class AddInventoryProduct(BaseModel):
    inventory_id: str
    product_id: Optional[str] = None
    is_bundle: Optional[bool] = False
    ean: Optional[str] = None
    sku: Optional[str] = None
    tax_rate: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    average_cost: Optional[float] = None
    star: Optional[int] = None
    manufacturer_id: Optional[int] = None
    category_id: Optional[int] = None
    prices: Optional[Dict[str, float]] = None
    stock: Optional[Dict[str, int]] = None
    locations: Optional[Dict[str, str]] = None
    text_fields: Optional[Dict[str, Union[str, Dict]]] = None
    images: Optional[Dict[int, str]] = None
    links: Optional[Dict[str, Dict]] = None
    bundle_products: Optional[Dict[str, int]] = None

    @classmethod
    def from_auction(cls, inventory_id, author, auction, match_manufacturer, match_category):
        """
        Converts an Auction object into an AddInventoryProduct instance.
        """
        # Map basic auction fields
        product_name = auction.name
        description = auction.description if auction.description else ""
        price_euro = auction.price_euro
        category = match_category(auction.category)
        # manufacturer = match_manufacturer(auction.manufacturer)
        photoset = auction.photoset

        photos = list(map(lambda photo: os.path.join(settings.MEDIA_ROOT, photoset.directory_location, photo.name), photoset.photos.all()))
        photos = parse_photos(photos)
        photos = limit_photo_size(photos)
        photos = {i: photo for i, photo in enumerate(photos)}
        # Add parameters (features) from AuctionParameter
        parameters = AuctionParameter.objects.filter(auction=auction)
        features = {param.parameter.name: param.value_name for param in parameters}

        sku_code = f"{author} SP_{int(auction.shipment_price)} {price_euro} {photoset.thumbnail.name} {photoset.directory_location}"

        # Create product dictionary
        product_data = {
            "inventory_id": str(inventory_id),
            "ean": auction.serial_numbers,
            "weight": map_shipment_to_weight(auction.shipment_price),
            "sku": sku_code,
            "prices": {"1184": float(auction.price_pln)},
            "category_id": category,
            # "manufacturer_id": manufacturer,
            "text_fields": {
                "name": product_name,
                "description": description,
                "description|de": description,
                "features": features,
            },
            "images": photos,
            "stock": {
                "bl_1855": auction.amount,
            }
        }

        return cls(**product_data)


class AddInventoryProductResponse(BaseModel):
    status: str  # "SUCCESS" or "ERROR"
    product_id: Optional[Union[str, int]] = None  # The ID of the newly added product in BaseLinker
    warnings: Optional[Dict[str, str]] = None  # Any warnings related to the product addition

    @classmethod
    def from_response(cls, response: Dict):
        """
        Process the API response into an AddInventoryProductResponse instance.
        """
        return cls(
            status=response.get("status"),
            product_id=response.get("product_id"),
            warnings=response.get("warnings"),
        )

    class Config:
        schema_extra = {
            "example": {
                "status": "ERROR",
                "product_id": "2685",
                "warnings": {
                    "image_error": "Image at index 1 could not be processed"
                }
            }
        }