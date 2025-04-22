from collections import defaultdict
from typing import Dict, Optional

from ..models.translations import ParameterTranslation, AuctionParameterTranslation
from ..models.addInventoryProduct import get_category_tags_field_name, prepare_tags
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

def get_translations(auction_parameter):
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

def translate_features_dict(
    features: Dict[str, str],
    category_id: Optional[int] = None,
    serial_numbers: Optional[str] = None,
    name: Optional[str] = None,
    tags: Optional[str] = None,
    language: str = "de"
) -> Dict[str, str]:
    translated: Dict[str, str] = {}
    to_translate: Dict[str, str] = {}

    # 1. Hardcoded custom translations
    translated.update(add_custom_translations(features))

    # 2. DB/AI for the rest, skipping already-handled or function-translated keys
    for k, v in features.items():
        if k in FUNCTION_TRANSLATED_PARAMETERS or k in translated:
            continue
        # Build a mock with the real allegro_id if available (assuming features keys came from real AuctionParameter objects)
        mock_param = type("MockParam", (), {
            "parameter": type("Mock", (), {"name": k, "allegro_id": None}),
            "value_name": v
        })()
        t = get_translations(mock_param)
        param_trans = t["parameter_translation"] or k
        value_trans = t["value_translation"]
        if param_trans and value_trans:
            translated[param_trans] = value_trans
        elif param_trans:
            to_translate[param_trans] = v
        else:
            to_translate[k] = v

    # 3. AI fallback
    if to_translate:
        try:
            openai = OpenAiService()
            ai_translations = openai.translate_parameters(to_translate)
            translated.update(ai_translations)
        except Exception as e:
            print(f"[WARN] AI translation failed: {e}")

    # 4. Always append fixed reference fields
    if serial_numbers is not None:
        translated["Herstellernummer"] = serial_numbers
    if category_id is not None and features.get(get_category_tags_field_name(category_id)):
        translated["OE/OEM Referenznummer(n)"] = features[
            get_category_tags_field_name(category_id)
        ].replace("|", ",")
    if category_id is not None and name is not None and tags is not None:
        translated["Vergleichsnummer"] = prepare_tags(category_id, name, tags, language)

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