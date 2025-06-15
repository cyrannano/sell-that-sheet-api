import os
import logging
import requests
import json
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from django.conf import settings

from .feature_translation_service import translate_name_description, translate_features_dict
from .utils import prepare_temp_directory, remove_temp_directory
from ..models import AddInventoryProduct, AddInventoryProductResponse
from .allegroconnector import AllegroConnector

from ..models import AuctionSet
from ..models.addInventoryProduct import prepare_tags, get_category_tags_field_name, \
    get_category_part_number_field_name, get_category_auto_tags_field_name, calculate_price_euro, map_shipment_to_weight

logger = logging.getLogger(__name__)

BASELINKER_TO_ALLEGRO_CATEGORY_ID = {
    '966013':'313853',
    '967175':'256695',
    '213362':'254664',
    '213388':'261281',
    '213757':'261282',
    '213376':'254683',
    '213519':'254684',
    '997582':'254684',
    '213393':'254685',
    '213690':'254688',
    '213907':'254687',
    '283619':'261283',
    '213734':'254659',
    '213696':'254661',
    '213917':'254663',
    '213607':'254662',
    '972409':'261292',
    '213667':'254599',
    '213377':'254580',
    '910036':'254600',
    '213624':'254601',
    '213396':'254602',
    '910037':'254603',
    '213960':'254581',
    '420906':'254605',
    '213761':'254606',
    '891998':'254608',
    '213918':'254638',
    '213518':'254639',
    '420907':'254640',
    '213679':'254642',
    '436161':'254644',
    '384531':'254550',
    '213615':'254551',
    '213359':'254548',
    '213605':'254557',
    '910035':'254552',
    '213466':'254553',
    '420797':'254554',
    '349487':'254555',
    '213448':'254556',
    '213512':'261294',
    '506590':'261296',
    '213358':'18711',
    '213381':'18712',
    '213507':'18713',
    '213922':'254560',
    '911718':'254561',
    '213360':'254559',
    '213683':'254562',
    '213443':'254563',
    '213370':'254564',
    '213367':'254565',
    '213449':'254578',
    '213403':'18708',
    '213729':'261287',
    '213374':'254518',
    '994520':'254518',
    '213755':'254519',
    '213731':'261284',
    '213698':'249303',
    '213399':'4095',
    '213372':'254522',
    '213924':'254524',
    '213401':'254521',
    '213675':'254523',
    '991616':'261285',
    '213722':'261280',
    '213389':'254525',
    '213404':'18720',
    '420908':'254526',
    '213974':'146544',
    '892747':'261297',
    '213921':'18719',
    '213513':'18718',
    '213556':'18717',
    '404559':'146543',
    '438814':'261288',
    '408643':'261152',
    '213384':'254700',
    '996928':'254701',
    '213353':'254701',
    '213392':'254702',
    '213363':'254703',
    '213791':'254706',
    '213373':'254704',
    '213408':'254705',
    '213351':'254699',
    '213526':'254718',
    '549393':'49237',
    '431424':'49240',
    '213916':'49241',
    '213925':'250545',
    '213673':'258676',
    '415223':'258675',
    '213506':'261075',
    '213355':'256999',
    '885824':'256998',
    '213520':'4136',
    '213871':'18800',
    '497803':'18798',
    '213371':'255100',
    '996919':'255099',
    '213365':'255099',
    '213694':'255105',
    '213378':'255103',
    '213350':'255102',
    '214137':'255121',
    '213356':'255119',
    '213614':'255122',
    '450289':'255139',
    '213906':'4135',
    '213926':'256287',
    '910034':'261078',
    '213446':'261076',
    '213678':'629',
    '922031':'255442',
    '892471':'50840',
    '213923':'50841',
    '213390':'256227',
    '213380':'256224',
    '213402':'256223',
    '213912':'50822',
    '213836':'256142',
    '213588':'255520',
    '213864':'255521',
    '908884':'255457',
    '885844':'255458',
    '908885':'255456',
    '931550':'312565',
    '910038':'255507',
    '513008':'147922',
    '213661':'255509',
    '213911':'255511',
    '213460':'50860',
    '213592':'255516',
    '213723':'50861',
    '213409':'251083',
    '213410':'251084',
    '213385':'251082',
    '213398':'260783',
    '213397':'252810',
    '213662':'251086',
    '213455':'18698',
    '213406':'251122',
    '213611':'256242',
    '213456':'251124',
    '546828':'251103',
    '965965':'251102',
    '903324':'251127',
    '213386':'251105',
    '213557':'251104',
    '213669':'18697',
    '899098':'4142',
    '213606':'256161',
    '213639':'261299',
    '891996':'260606',
    '213354':'256164',
    '213589':'260605',
    '213509':'261072',
    '424343':'256162',
    '213638':'256163',
    '213352':'50745',
    '213719':'255609',
    '962592':'50753',
    '213400':'50754',
    '420798':'255612',
    '213870':'4147',
    '375880':'50755',
    '506589':'261563',
    '213721':'255613',
    '213733':'4145',
    '213713':'261054',
    '375879':'50770',
    '213672':'50771',
    '213681':'261066',
    '524674':'320761',
    '375882':'50766',
    '409671':'256283',
    '380501':'256285',
    '213510':'256282',
    '214059':'256182',
    '213613':'50765',
    '881993':'50776',
    '924815':'50777',
    '213508':'261300',
    '995506':'261300',
    '910033':'260615',
    '360585':'260614',
    '357866':'260579',
    '533234':'250403',
    '899099':'250405',
    '213503':'250406',
    '213514':'250427',
    '213464':'250407',
    '213693':'18839',
    '213716':'18843',
    '903325':'250429',
    '357865':'260616',
    '213720':'260617',
    '214136':'260618',
    '213676':'260619',
    '965964':'250431',
    '357868':'18842',
    '423778':'260948',
    '925018':'250843',
    '213560':'250844',
    '513009':'250845',
    '213622':'250846',
    '213561':'250862',
    '213590':'250850',
    '213559':'250847',
    '213454':'250848',
    '213993':'250849',
    '213563':'258678',
    '492813':'260953',
    '213712':'258697',
    '238042':'258685',
    '213955':'258689',
    '213570':'258691',
    '213686':'258693',
    '886069':'258696',
    '213593':'260923',
    '213872':'50867',
    '213594':'50868',
    '921539':'256002',
    '408642':'256004',
    '213469':'256006',
    '213595':'256008',
    '213680':'50873',
    '421002':'256018',
    '213809':'256011',
    '513007':'256012',
    '213610':'256014',
    '213717':'256016',
    '213873':'50884',
    '314851':'260941',
    '375877':'261089',
    '921957':'255917',
    '213710':'255923',
    '421001':'256226',
    '883279':'255920',
    '238108':'255930',
    '938682':'255934',
    '214155':'255925',
    '975033':'258679',
    '213677':'261301',
    '213688':'258681',
    '213991':'258686',
    '213612':'258690',
    '306033':'259307',
    '881994':'18864',
    '213383':'255640',
    '360588':'255642',
    '213666':'255643',
    '954282':'260942',
    '213730':'255644',
    '213407':'18866',
    '213405':'255661',
    '213387':'255658',
    '922029':'255659',
    '213668':'255660',
    '375883':'255645',
    '423779':'255646',
    '213463':'19063',
    '350523':'260723',
    '546827':'250863',
    '213461':'250867',
    '213459':'250868',
    '213457':'260731',
    '357867':'260724',
    '213753':'18962',
    '922983':'250869',
    '213453':'8687',
    '213931':'18965',
    '213458':'260730',
    '213450':'250876',
    '213754':'250878',
    '436162':'260729',
    '251312':'250883',
    '251313':'250884',
    '213558':'250885',
    '993626':'260722',
    '421000':'260722',
    '213562':'256099',
    '213501':'256100',
    '213879':'256101',
    '925019':'261082',
    '420910':'260725',
    '914337':'258702',
    '213366':'250902',
    '485521':'261223',
    '365655':'256139',
    '549394':'254180',
    '213709':'254181',
    '475050':'254183',
    '213618':'261224',
    '213671':'254184',
    '213762':'254185',
    '213364':'254186',
    '213929':'254187',
    '213674':'256104',
    '213382':'256035',
    '213587':'18886',
    '409247':'250282',
    '213555':'8682',
    '213984':'256029',
    '433126':'256031',
    '213630':'4133',
    '486268':'250222',
    '213707':'147885',
    '213517':'4134',
    '213714':'18888',
    '885843':'261303',
    '213511':'250553',
    '213692':'250224',
    '213617':'250302',
    '213932':'18891',
    '213516':'18892',
    '213609':'18894',
    '213689':'250243',
    '885976':'18893',
    '213745':'18895',
    '213515':'18896',
    '375881':'250223',
    '213685':'256105',
    '213684':'4132',
    '492812':'18897',
    '213628':'18898',
    '213744':'250242',
    '213687':'250550',
    '213756':'250552',
    '213379':'250548',
    '213626':'250549',
    '213933':'250551',
    '213554':'256032',
    '213691':'250285',
    '213718':'256034',
    '251310':'18900',
    '213715':'259627',
    '213361':'257711',
    '213976':'257712',
    '213616':'257714',
    '921538':'257716',
    '214156':'257698',
    '214153':'257692',
    '213621':'257689',
    '213901':'257691',
    '396318':'257625',
    '347411':'257626',
    '214149':'257629',
    '213697':'257631',
    '310450':'257634',
    '921111':'253533',
    '921110':'253536',
    '966012':'253549',
    '902391':'253559',
    '214158':'253561',
    '213357':'253562',
    '213629':'253565',
    '213619':'257407',
    '213568':'253569',
    '213375':'253572',
    '498231':'256641',
    '891997':'257361',
    '213391':'253590',
    '492811':'253598',
    '214146':'253775',
    '501918':'253780',
    '214151':'253784',
}


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

    def translate_existing_products_to_language(self, auctionset, language: str = "de") -> List[
        AddInventoryProductResponse]:
        responses = []
        for auction in auctionset.auctions.all():
            try:
                product = AddInventoryProduct.from_auction(
                    inventory_id=self.inventory_id,
                    auction=auction,
                    match_manufacturer=self.match_manufacturer,
                    match_category=self.match_category,
                    owner=auctionset.owner,
                    author=auctionset.creator,
                )

                # Filter text_fields only for the target language
                text_fields = {}
                for key, value in product.text_fields.items():
                    if f"|{language}" in key or key.endswith(f"|{language}"):
                        text_fields[key] = value

                update_payload = {
                    "inventory_id": product.inventory_id,
                    "product_id": product.product_id or auction.product_id,  # fallback if needed
                    "text_fields": text_fields,
                }

                response = self._post("addInventoryProduct", update_payload)
                responses.append(AddInventoryProductResponse.from_response(response))
            except Exception as e:
                logger.error(f"Translation update failed for auction {auction.id}: {e}")
        return responses


    def translate_product_parameters(
            self,
            product_ids: List[int],
            target_lang: str = "de",
            inventory_id: int = 1430
    ) -> List[Dict]:
        logger.info(f"Translating parameters to '{target_lang}' for products: {product_ids}")
        responses = []

        try:
            product_data = self._post("getInventoryProductsData", {
                "inventory_id": inventory_id,
                "products": product_ids,
            }).get("products", {})

            for product_id, product in product_data.items():
                text_fields = product.get("text_fields", {})
                features = text_fields.get("features")
                product_price_pln = product.get("prices", {}).get("1184")
                product_price_euro = product.get("prices", {}).get("4848")
                product_weight = product.get("weight")

                product_name, product_description = text_fields.get("name"), text_fields.get("description", text_fields.get("description_extra4"))
                product_category = product.get("category_id")
                product_allegro_category_id = int(BASELINKER_TO_ALLEGRO_CATEGORY_ID.get(str(product_category)))
                product_serial_numbers = features.get(get_category_part_number_field_name(product_allegro_category_id))
                product_tags = features.get(get_category_auto_tags_field_name(product_allegro_category_id)) or ""

                if product_tags:
                    del features[get_category_auto_tags_field_name(product_allegro_category_id)]
                if product_serial_numbers:
                    del features[get_category_part_number_field_name(product_allegro_category_id)]

                auto_tags = prepare_tags(
                    product_allegro_category_id, product_name, product_tags
                )

                translated_name, translated_description = translate_name_description(
                    product_name,
                    product_description,
                    product_allegro_category_id,
                    target_lang,
                )

                if not translated_name or (
                        not translated_description and product_description is not None and product_description.strip() != ''):
                    logger.warning(f"Product {product_id} has no name or description to translate.")
                    continue

                if not features:
                    logger.warning(f"Product {product_id} has no features to translate.")
                    continue

                translated_features = self._translate_features(features, target_lang, product_allegro_category_id, product_serial_numbers, auto_tags, product_name)

                update_payload = {
                    "inventory_id": inventory_id,
                    "product_id": str(product_id),
                    "text_fields": {
                        f"name|{target_lang}": translated_name,
                        f"description_extra1|{target_lang}": translated_description,
                        f"features|{target_lang}": translated_features
                    }
                }

                if product_weight and not product_price_euro:
                    update_payload["prices"] = {
                        "4848": calculate_price_euro(product_price_pln, int(product_weight))
                    }

                logger.info(f"Updating product {product_id} with {target_lang} features: {translated_features}")
                result = self._post("addInventoryProduct", update_payload)
                responses.append({"product_id": product_id, "status": result.get("status")})

        except Exception as e:
            logger.error("Error while translating product parameters", exc_info=e)
            raise

        return responses

    def _translate_features(self, features, target_lang, category_id, serial_numbers, auto_tags, product_name):
        translated_features = translate_features_dict(features=features, language=target_lang, category_id=category_id,
                                                      serial_numbers=serial_numbers, tags=auto_tags, name=product_name)

        return translated_features
