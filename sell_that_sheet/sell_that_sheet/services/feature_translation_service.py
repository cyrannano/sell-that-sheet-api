from collections import defaultdict
from typing import Dict, Optional, Union, List

from django.db.models import QuerySet

from ..models import Auction, AuctionParameter
from ..models.translations import ParameterTranslation, AuctionParameterTranslation
from ..services.openaiservice import OpenAiService

PARAMETER_SEPARATOR = "|"

def translate_bolt_pattern(param):
    values = param.split('x')
    return {
        "Lochzahl": f'{values[0]}',
        "Lochkreis": f'{values[1]} mm',
    }

def translate_offset(param):
    return {"Einpresstiefe (ET)": f'{param} mm'}

def translate_rim_diameter(param):
    return {"Zollgröße": param.replace('"','').replace(".", ",")}

def translate_rim_width(param):
    return {"Felgenbreite": param.replace('"', '').replace(".", ",").strip()}

CUSTOM_TRANSLATIONS = defaultdict(lambda: lambda _: {})

FUNCTION_TRANSLATED_PARAMETERS = [
    "Rozstaw śrub",
    "Odsadzenie (ET)",
    "Średnica felgi",
    "Szerokość felgi",
    ]

CUSTOM_TRANSLATIONS.update({
    "Rozstaw śrub": translate_bolt_pattern,
    "Odsadzenie (ET)": translate_offset,
    "Średnica felgi": translate_rim_diameter,
    "Szerokość felgi": translate_rim_width,
})

def add_custom_translations(features: Dict[str, str]) -> Dict[str, str]:
    tmp_dict: Dict[str, str] = {}
    for key, val in features.items():
        if key in CUSTOM_TRANSLATIONS:
            try:
                tmp_dict.update(CUSTOM_TRANSLATIONS[key](val))
            except Exception:
                continue
    return tmp_dict

def get_translation_auction_parameter(auction_parameter: AuctionParameter):
    """
        Retrieve translations for AuctionParameter's value_name and Parameter's name.
        First, try to find a translation using allegro_id.
        Then, search for the exact value_name inside the fetched queryset.
        """
    # Fetch translation for the parameter
    parameter_translation = ParameterTranslation.objects.filter(
        parameter=auction_parameter.parameter
    ).first()

    # Fetch all possible translations using allegro_id
    auction_parameter_translations = AuctionParameterTranslation.objects.filter(
        auction_parameter__parameter__allegro_id=auction_parameter.parameter.allegro_id
    )

    values = []
    if PARAMETER_SEPARATOR in auction_parameter.value_name:
        values = auction_parameter.value_name.split(PARAMETER_SEPARATOR)
    else:
        values.append(auction_parameter.value_name)

    translated_values = []

    for value in values:
        # Find the specific translation by matching value_name inside the queryset
        auction_parameter_translation = auction_parameter_translations.filter(
            auction_parameter__value_name=value
        ).first()
        translated_values.append(auction_parameter_translation.translation if auction_parameter_translation else None)

    return {
        "parameter_translation": parameter_translation.translation if parameter_translation else None,
        "value_translation": PARAMETER_SEPARATOR.join(translated_values) if None not in translated_values else None,
    }
def get_translations(
    param: Union[Dict[str, Union[str, int]], AuctionParameter]
) -> Dict[str, Optional[str]]:
    """
    Retrieve parameter and value translations from DB. Supports either:
      - a dict with keys 'name', 'value_name', and optional 'allegro_id'
      - an AuctionParameter-like object with .parameter.name, .parameter.allegro_id, and .value_name
    """
    # Unpack inputs
    if isinstance(param, dict):
        name = param.get("name")
        value_name = param.get("value_name", "")
    else:
        return get_translation_auction_parameter(param)

    # Lookup parameter translation by allegro_id or name
    param_qs = ParameterTranslation.objects.filter(
        parameter__name=name
    )
    parameter_translation = param_qs.first()

    # Lookup value translations
    apt_qs = AuctionParameterTranslation.objects.filter(
        auction_parameter__parameter__name=name
    )

    # Handle multiple split values
    values = (
        value_name.split(PARAMETER_SEPARATOR)
        if PARAMETER_SEPARATOR in value_name
        else [value_name]
    )
    translated_values = []
    for v in values:
        entry = apt_qs.filter(auction_parameter__value_name=v).first()
        translated_values.append(entry.translation if entry else None)

    return {
        "parameter_translation": parameter_translation.translation if parameter_translation else None,
        "value_translation": (
            PARAMETER_SEPARATOR.join(translated_values)
            if None not in translated_values
            else None
        ),
    }

def translate_features_dict(
    features: Union[Dict[str, str], List[AuctionParameter]],
    category_id: Optional[int] = None,
    serial_numbers: Optional[str] = None,
    name: Optional[str] = None,
    tags: Optional[str] = None,
    language: str = "de",
    auction_parameters: Optional[QuerySet[AuctionParameter]] = None
) -> Dict[str, str]:
    """
    Translates feature key→value dict using:
      1. Hardcoded translations
      2. DB lookups
      3. AI fallback
      4. Always appends reference fields
    """
    translated: Dict[str, str] = {}
    to_translate: Dict[str, str] = {}
    from ..models.addInventoryProduct import (
        get_category_tags_field_name,
        get_category_part_number_field_name,
        get_category_auto_tags_field_name,
        prepare_tags,
    )
    from .baselinkerservice import BASELINKER_TO_ALLEGRO_CATEGORY_ID

    # 1. Hardcoded translations
    translated.update(add_custom_translations(features))

    untranslated_fields = set()
    if category_id is not None:
        untranslated_fields.update(
            {
                get_category_part_number_field_name(category_id),
                get_category_tags_field_name(category_id),
                get_category_auto_tags_field_name(category_id),
            }
        )

    # 2. DB/AI translation for remaining keys

    for key, value in features.items():

        if key in FUNCTION_TRANSLATED_PARAMETERS or key in translated or key in untranslated_fields:
            continue
        # Use dict input to get_translations

        t = get_translations({"name": key, "value_name": value})

        param_trans = t.get("parameter_translation") or key
        value_trans = t.get("value_translation")
        if param_trans and value_trans:
            translated[param_trans] = value_trans
        elif param_trans:
            to_translate[param_trans] = value
        else:
            to_translate[key] = value

    if auction_parameters:
        for parameter in auction_parameters:
            t = get_translations(parameter)

            param_trans = t.get("parameter_translation") or key
            value_trans = t.get("value_translation")

            if param_trans and value_trans:
                translated[param_trans] = value_trans
            elif param_trans:
                to_translate[param_trans] = parameter.value_name
            else:
                to_translate[key] = parameter.value_name

    # 3. AI fallback
    if to_translate:
        try:
            ai = OpenAiService()
            ai_trans = ai.translate_parameters(to_translate)
            translated.update(ai_trans)
        except Exception as e:
            print(f"[WARN] AI translation failed: {e}")

    # 4. Append fixed fields
    if serial_numbers is not None:
        translated["Herstellernummer"] = serial_numbers
    tag_field = (
        features.get(get_category_tags_field_name(category_id))
        if category_id is not None
        else None
    )
    if tag_field:
        translated["OE/OEM Referenznummer(n)"] = tag_field.replace("|", ",")
    if category_id and name and tags:
        translated["Vergleichsnummer"] = prepare_tags(
            category_id, name, tags, language
        )

    return translated

def translate_name_description(name, description, allegro_category_id, target_language):
    openai_service = OpenAiService()
    try:
        translation = openai_service.translate_completion(title=name, description=description, category=allegro_category_id)
        translated_description = translation.get("description", "")
        translated_product_name = translation.get("title", "")
    except Exception as e:
        return None, None

    return translated_product_name, translated_description