import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from nutrition.models import Product, Nutrient, ProductNutrient


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = "Import USDA FoodData Central Foundation Foods JSON into DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="data/FoodData_Central_foundation_food_json_2025-12-18.json",
            help="Path to USDA JSON file",
        )
        parser.add_argument("--limit", type=int, default=100, help="Limit foods to import (0 = all)")
        parser.add_argument("--dry-run", action="store_true", help="Parse file but do not write to DB")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        limit = int(options["limit"])
        dry_run = bool(options["dry_run"])

        if not path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        self.stdout.write(f"Loading JSON: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))

        foods = payload.get("FoundationFoods") or payload.get("foundationFoods")
        if not isinstance(foods, list):
            self.stderr.write(self.style.ERROR("Unexpected JSON structure: expected key 'FoundationFoods'"))
            self.stderr.write(self.style.WARNING(f"Top-level keys: {list(payload.keys())[:30]}"))
            return

        if limit > 0:
            foods = foods[:limit]

        created_products = updated_products = 0
        created_nutrients = updated_nutrients = 0
        created_links = updated_links = 0

        for food in foods:
            fdc_id = food.get("fdcId")
            name = food.get("description")
            if not fdc_id or not name:
                continue

            category = None
            food_category = food.get("foodCategory") or {}
            if isinstance(food_category, dict):
                category = food_category.get("description")

            if dry_run:
                continue

            product, was_created = Product.objects.update_or_create(
                usda_fdc_id=int(fdc_id),
                defaults={
                    "name": name,
                    "category": category,
                    "data_source": "USDA",
                    "is_active": True,
                },
            )
            if was_created:
                created_products += 1
            else:
                updated_products += 1

            for fn in food.get("foodNutrients", []) or []:
                nutrient_data = fn.get("nutrient") or {}
                usda_nutrient_id = nutrient_data.get("id")
                nutrient_name = nutrient_data.get("name")
                unit = nutrient_data.get("unitName")
                amount = fn.get("amount")

                amount_dec = to_decimal(amount)
                if usda_nutrient_id is None or not nutrient_name or not unit or amount_dec is None:
                    continue

                unit_norm = str(unit)

                nutrient, n_created = Nutrient.objects.update_or_create(
                    usda_nutrient_id=int(usda_nutrient_id),
                    defaults={"name": nutrient_name, "unit": unit_norm},
                )
                if n_created:
                    created_nutrients += 1
                else:
                    updated_nutrients += 1

                link, l_created = ProductNutrient.objects.update_or_create(
                    product=product,
                    nutrient=nutrient,
                    defaults={"amount_per_100g": amount_dec, "data_source": "USDA"},
                )
                if l_created:
                    created_links += 1
                else:
                    updated_links += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no DB writes performed."))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Products +{created_products} (updated {updated_products}); "
                f"Nutrients +{created_nutrients} (updated {updated_nutrients}); "
                f"Links +{created_links} (updated {updated_links})"
            )
        )