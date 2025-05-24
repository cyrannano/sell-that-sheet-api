from django.core.management.base import BaseCommand
from sell_that_sheet.services.allegroconnector import AllegroConnector, export_catalogue_to_xlsx

class Command(BaseCommand):
    help = 'Export all auctions with parameters from allegro to an XLSX file'

    def handle(self, *args, **kwargs):
        connector = AllegroConnector()
        connector.get_allegro_access_token()
        catalogue = connector.download_catalogue()

        # Export to Excel
        export_catalogue_to_xlsx(catalogue, "my_allegro_catalogue.xlsx")
