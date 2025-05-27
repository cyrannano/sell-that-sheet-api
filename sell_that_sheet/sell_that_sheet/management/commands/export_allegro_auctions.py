from django.core.management.base import BaseCommand
from sell_that_sheet.services.allegroconnector import AllegroConnector

class Command(BaseCommand):
    help = 'Export all auctions with parameters from allegro to an XLSX file'

    def handle(self, *args, **kwargs):
        connector = AllegroConnector()
        connector.get_allegro_access_token()
        catalogue = connector.download_catalogue()

        parsed = connector.parse_catalogue(catalogue)

        # save parsed to json file
        with open('parsed_catalogue.json', 'w') as f:
            import json
            json.dump(parsed, f, indent=4)

        connector.export_to_xlsx(parsed, 'full_catalogue.xlsx')
