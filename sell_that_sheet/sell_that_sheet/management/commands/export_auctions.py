import pandas as pd
from django.core.management.base import BaseCommand
from sell_that_sheet.models import Auction, AuctionParameter
from django.db.models import Prefetch
from django.utils.timezone import is_aware

class Command(BaseCommand):
    help = 'Export all auctions with parameters to an XLSX file'

    def handle(self, *args, **kwargs):
        auctions = Auction.objects.prefetch_related(
            Prefetch('auctionparameter_set', queryset=AuctionParameter.objects.select_related('parameter'))
        ).all()

        param_names = set()
        for auction in auctions:
            for ap in auction.auctionparameter_set.all():
                param_names.add(ap.parameter.name)

        param_names = sorted(param_names)

        static_fields = [
            "id", "name", "thumbnail name", "price_pln", "price_euro", "tags", "serial_numbers",
            "photoset_id", "shipment_price", "description", "category",
            "created_at", "amount", "translated_params"
        ]
        headers = static_fields + param_names

        rows = []
        for auction in auctions:
            # Safely convert to timezone-naive
            created_at = auction.created_at
            if is_aware(created_at):
                created_at = created_at.replace(tzinfo=None)



            thumbnail_img_name  = auction.photoset.thumbnail.name.split('.')[0]

            row = [
                auction.id,
                auction.name,
                thumbnail_img_name,
                auction.price_pln,
                auction.price_euro,
                auction.tags,
                auction.serial_numbers,
                auction.photoset_id,
                auction.shipment_price,
                auction.description,
                auction.category,
                created_at,
                auction.amount,
                auction.translated_params,
            ]

            param_map = {ap.parameter.name: ap.value_name for ap in auction.auctionparameter_set.all()}
            for pname in param_names:
                row.append(param_map.get(pname))
            rows.append(row)

        df = pd.DataFrame(rows, columns=headers)

        # Explicit conversion of datetime columns to timezone-naive
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)

        output_path = 'auctions_export.xlsx'
        df.to_excel(output_path, index=False)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported auctions to {output_path}'))