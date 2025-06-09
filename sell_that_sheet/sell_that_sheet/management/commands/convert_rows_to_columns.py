from django.core.management.base import BaseCommand, CommandError
from sell_that_sheet.services.rows_to_columns import rows_to_columns


class Command(BaseCommand):
    help = "Convert a row based file into a column oriented XLSX file"

    def add_arguments(self, parser):
        parser.add_argument(
            "input_path", type=str, help="Path to the row based input file"
        )
        parser.add_argument(
            "xlsx_path", type=str, help="Path for the resulting XLSX file"
        )

    def handle(self, *args, **options):
        input_path = options["input_path"]
        xlsx_path = options["xlsx_path"]
        try:
            rows_to_columns(input_path, xlsx_path)
        except Exception as e:
            raise CommandError(f"Error converting file to XLSX: {e}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully converted {input_path} to {xlsx_path}")
        )
