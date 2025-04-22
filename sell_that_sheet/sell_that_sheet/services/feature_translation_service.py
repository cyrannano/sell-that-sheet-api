from collections import defaultdict
from typing import Dict, Optional, Union

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

def get_translations(
    param: Union[Dict[str, Union[str, int]], object]
) -> Dict[str, Optional[str]]:
    """
    Retrieve parameter and value translations from DB. Supports either:
      - a dict with keys 'name', 'value_name', and optional 'allegro_id'
      - an AuctionParameter-like object with .parameter.name, .parameter.allegro_id, and .value_name
    """
    # Unpack inputs
    if isinstance(param, dict):
        name = param.get("name")
        allegro_id = param.get("allegro_id")
        value_name = param.get("value_name", "")
    else:
        name = param.parameter.name
        allegro_id = getattr(param.parameter, "allegro_id", None)
        value_name = param.value_name or ""

    # Lookup parameter translation by allegro_id or name
    if allegro_id:
        param_qs = ParameterTranslation.objects.filter(
            parameter__allegro_id=allegro_id
        )
    else:
        param_qs = ParameterTranslation.objects.filter(
            parameter__name=name
        )
    parameter_translation = param_qs.first()

    # Lookup value translations
    if allegro_id:
        apt_qs = AuctionParameterTranslation.objects.filter(
            auction_parameter__parameter__allegro_id=allegro_id
        )
    else:
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
    features: Dict[str, str],
    category_id: Optional[int] = None,
    serial_numbers: Optional[str] = None,
    name: Optional[str] = None,
    tags: Optional[str] = None,
    language: str = "de",
    django_model_source=False
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
    from ..models.addInventoryProduct import get_category_tags_field_name, prepare_tags
    from .baselinkerservice import BASELINKER_TO_ALLEGRO_CATEGORY_ID

    # 1. Hardcoded translations
    translated.update(add_custom_translations(features))

    # 2. DB/AI translation for remaining keys
    for key, value in features.items():
        if key in FUNCTION_TRANSLATED_PARAMETERS or key in translated:
            continue
        # Use dict input to get_translations
        allegro_cat_id = category_id if django_model_source else int(BASELINKER_TO_ALLEGRO_CATEGORY_ID.get(str(category_id)))
        t = get_translations({"name": key, "value_name": value, "allegro_id": allegro_cat_id})
        param_trans = t.get("parameter_translation") or key
        value_trans = t.get("value_translation")
        if param_trans and value_trans:
            translated[param_trans] = value_trans
        elif param_trans:
            to_translate[param_trans] = value
        else:
            to_translate[key] = value

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