# Generated by Django 5.0.3 on 2024-09-15 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sell_that_sheet", "0005_auction_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="auction",
            name="category",
            field=models.CharField(max_length=15, null=True),
        ),
    ]