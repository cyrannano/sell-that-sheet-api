from celery import shared_task
from django.conf import settings
from .services.allegroconnector import AllegroConnector
from django.core.management import call_command
import os


@shared_task
def export_allegro_catalogue_task():
    connector = AllegroConnector()
    connector.get_allegro_access_token()
    catalogue = connector.download_catalogue()
    parsed = connector.parse_catalogue(catalogue)
    output_path = os.path.join(settings.BASE_DIR, "full_catalogue.xlsx")
    connector.export_to_xlsx(parsed, output_path)
    return output_path


@shared_task
def export_auctions_task():
    call_command("export_auctions")
    return os.path.join(settings.BASE_DIR, "auctions_export.xlsx")
