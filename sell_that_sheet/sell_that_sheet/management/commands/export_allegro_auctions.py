from django.core.management.base import BaseCommand
from sell_that_sheet.services.allegroconnector import AllegroConnector

class Command(BaseCommand):
    help = 'Export all auctions with parameters from allegro to an XLSX file'

    def handle(self, *args, **kwargs):
        connector = AllegroConnector()
        catalogue = connector.download_catalogue()

        # Export to Excel
        connector.export_catalogue_to_xlsx(catalogue, "my_allegro_catalogue.xlsx")
