# Generated by Django 5.0.3 on 2024-09-04 06:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sell_that_sheet", "0003_auctionset_creator"),
    ]

    operations = [
        migrations.AddField(
            model_name="auction",
            name="shipment_price",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="auction",
            name="price_euro",
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="auction",
            name="serial_numbers",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="auction",
            name="tags",
            field=models.CharField(max_length=255, null=True),
        ),
    ]