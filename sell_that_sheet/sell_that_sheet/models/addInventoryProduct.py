from django.db import models
import os
from typing import Dict, Optional, List, Union

from numpy.ma.core import divide

from .parameter import AuctionParameter
from django.conf import settings
from ..services.utils import parse_photos, limit_photo_size
from pydantic import BaseModel
import sqlite3
import re

conn = sqlite3.connect(settings.CUSTOM_PROPERTIES_DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def get_category_tags(category_id):
    cursor.execute("SELECT tags FROM category_tags WHERE category_id = ?", (category_id,))
    fetched = cursor.fetchone()
    if fetched is not None:
        return fetched[0]
    else:
        return None

def get_custom_tags():
    cursor.execute("SELECT key, value FROM custom_tags")
    return cursor.fetchall()


def create_dates_from_name(name, tags):
    # Strict regex for 1 or 2-digit year ranges
    res = re.search(r"\b(\d{1,2})-(\d{1,2})\b", name)
    from_tags = False

    # If not found in name, search in tags with parentheses
    if res is None:
        res = re.search(r"\((\d{1,2})-(\d{1,2})\)", tags)
        from_tags = True

    # If still not found, return empty string
    if res is None:
        return ''

    try:
        # Extract years
        date_start, date_end = map(int, res.groups())

        # Normalize years
        if 0 <= date_start <= 49:
            date_start += 2000
        elif 50 <= date_start <= 99:
            date_start += 1900

        if 0 <= date_end <= 49:
            date_end += 2000
        elif 50 <= date_end <= 99:
            date_end += 1900

        # Ensure date_start <= date_end
        if date_start > date_end:
            return ''  # Invalid range

        # Generate info string
        info_string = ' '.join(f"{year} {str(year)[2:]}" for year in range(date_start, date_end + 1))

        return info_string
    except Exception as e:
        # Log error for debugging
        print(f"Error processing dates: {e}")
        return ''

def map_shipment_to_weight(shipment):
    return settings.SHIPMENT_WEIGHT_MAPPING[int(float(shipment))]

def get_category_part_number_field_name(category_id):
    return "Numer katalogowy części"

def get_category_tags_field_name(category_id):
    return "Numer katalogowy oryginału"

def get_category_auto_tags_field_name(category):
    return "Numery katalogowe zamienników"

def add_side_to_tags(val):
    ret_val = ''
    if "prawa" in val.strip() or "prawy" in val.strip():
        ret_val += "prawa prawy prawe prawo "
    elif "lewa" in val.strip() or "lewy" in val.strip():
        ret_val += "lewa lewy lewe lewo "

    if "przód" in val.strip():
        ret_val += "przód przednie przedni przednia"
    elif "tył" in val.strip():
        ret_val += "tył tyłnie tylni tylna tylny"

    return ret_val

def remove_duplicates(string):
    return ' '.join(dict.fromkeys(string.split()))

def divideString(string, max_size=40, sep="|"):
    size = 0
    res_string = ''
    string = str(string).split()
    for x in range(len(string)):
        word = string[x]
        if (size + len(word) + 1 >= max_size):
            size = len(word)
            string[x - 1] += sep
        else:
            size += len(word) + 1

    for x in string:
        res_string += x
        if res_string[-1] != sep:
            res_string += ' '

    return res_string

def prepare_tags(category, name, tags):
    new_tags = ''
    try:
        for ct in get_custom_tags():
            if ct[0].upper() in name.upper() or ct[0].upper() in tags.upper():
                if ct[0].upper() == 'LIFT' and ct[0].upper() in name.upper():
                    if not 'LIFT ' in name.upper() or 'PRZED LIFT' in name.upper():
                        continue
                new_tags = str(new_tags) + " " + str(ct[1])
    except Exception as e:
        raise Exception("Nie udało się dodać własnych tagów\n" + str(e)) from e
        print("Nie udało się dodać własnych tagów", e)

    try:
        category_tags = get_category_tags(int(float(category)))
        if category_tags is not None:
            new_tags += " " + category_tags
    except Exception as e:
        raise Exception("Nie udało się dodać tagów z kategorii\n" + str(e)) from e
        print("Nie udało się dodać tagów z kategorii", e)


    new_tags += " " + create_dates_from_name(name, tags)
    new_tags += " " + add_side_to_tags(name)

    # remove duplicate words
    new_tags = remove_duplicates(new_tags)

    return divideString(new_tags.upper())

def safe_cast_int(val):
    try:
        return int(val)
    except:
        return ''

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
    def from_auction(cls, inventory_id, auction, match_manufacturer, match_category, owner, author):
        """
        Converts an Auction object into an AddInventoryProduct instance.
        """
        # Map basic auction fields
        product_name = auction.name
        product_name_de = auction.translated_params.get("de", {}).get("name", "") if auction.translated_params else ""
        description = auction.description if auction.description else ""
        description_de = auction.translated_params.get("de", {}).get("description", "") if auction.translated_params else ""
        price_euro = auction.price_euro
        category = match_category(auction.category)
        # manufacturer = match_manufacturer(auction.manufacturer)
        photoset = auction.photoset

        photos = list(map(lambda photo: os.path.join(settings.MEDIA_ROOT, photoset.directory_location, photo.name), photoset.photos.all()))
        # sort photos by name
        photos.sort()
        photos = parse_photos(photos)
        photos = limit_photo_size(photos)
        photos = {i: photo for i, photo in enumerate(photos)}
        # Add parameters (features) from AuctionParameter
        parameters = AuctionParameter.objects.filter(auction=auction)
        features = {param.parameter.name: param.value_name for param in parameters}

        # Add category specific fields
        features[get_category_part_number_field_name(auction.category)] = auction.serial_numbers
        features[get_category_tags_field_name(auction.category)] = divideString(remove_duplicates(auction.tags).upper())
        features[get_category_auto_tags_field_name(auction.category)] = prepare_tags(auction.category, auction.name, auction.tags)


        sku_code = f"{owner.username[0].upper()} {author.username.upper()[:3]} SP_{safe_cast_int(auction.shipment_price)} {safe_cast_int(price_euro)} {photoset.thumbnail.name.split('.')[0]} {photoset.directory_location}"

        star = author.star_id if author.star_id else 0

        # Find manufacturer
        manufacturer_parameter = filter(lambda x: "PRODUCENT" in x.parameter.name.upper() or "MARKA" in x.parameter.name.upper(), parameters).__next__()
        manufacturer = match_manufacturer(manufacturer_parameter.value_name)



        # Create product dictionary
        product_data = {
            "inventory_id": str(inventory_id),
            "ean": auction.serial_numbers,
            "weight": map_shipment_to_weight(auction.shipment_price),
            "sku": sku_code,
            "prices": {"1184": float(auction.price_pln)},
            "category_id": category,
            "star": int(star),
            "manufacturer_id": manufacturer,
            "text_fields": {
                "name": product_name,
                "name|de": product_name_de,
                "description": description,
                "description_extra1": description_de,
                "description_extra1|de": description_de,
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