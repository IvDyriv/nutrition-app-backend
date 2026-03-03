from django.core.management.base import BaseCommand
from django.db import transaction

from nutrition.models import Product, ProductNutrient


USDA_IDS = {
    "kcal": 1008,
    "protein": 1003,
    "fat": 1004,
    "carb": 1005,
}


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def compute_tags(kcal, protein_g, fat_g, carb_g):
    tags = []

    if kcal > 0 and kcal < 60:
        tags.append("low_cal")

    protein_kcal = protein_g * 4.0
    carb_kcal = carb_g * 4.0
    fat_kcal = fat_g * 9.0
    total_macro_kcal = protein_kcal + carb_kcal + fat_kcal

    if total_macro_kcal <= 0:
        return tags or ["balanced"]

    p = protein_kcal / total_macro_kcal * 100.0
    c = carb_kcal / total_macro_kcal * 100.0
    f = fat_kcal / total_macro_kcal * 100.0

    if p > 60:
        tags.append("protein")
        return tags
    if f > 60:
        tags.append("fat")
        return tags
    if c > 60:
        tags.append("carb")
        return tags

    pairs = [
        ("protein-fat", p, f),
        ("fat-carb", f, c),
        ("protein-carb", p, c),
    ]
    for name, primary, secondary in pairs:
        if primary > 40 and secondary > 25:
            tags.append(name)
            return tags

    tags.append("balanced")
    return tags


def compute_properties(kcal, protein_g, fat_g, carb_g):
    props = []

    if protein_g > 15:
        props.append("hi-proteine")
    if protein_g < 5:
        props.append("low-proteine")

    if fat_g > 15:
        props.append("hi-fat")
    if fat_g < 3:
        props.append("low-fat")

    if carb_g > 40:
        props.append("hi-carb")
    if carb_g < 5:
        props.append("low-carb")

    if kcal < 100:
        props.append("low-cal")
    if kcal > 200:
        props.append("hi-cal")

    return props


class Command(BaseCommand):
    help = "Compute denormalized tags/properties for products based on ProductNutrient amounts per 100g."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only-missing", action="store_true", help="Update only products with empty tags/properties")

    @transaction.atomic
    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        only_missing = options["only_missing"]

        qs = Product.objects.all().order_by("id")
        if only_missing:
            qs = qs.filter(tags=[], properties=[])

        if limit:
            qs = qs[:limit]

        updated = 0

        for product in qs:
            pn = (
                ProductNutrient.objects
                .filter(product=product, nutrient__usda_nutrient_id__in=USDA_IDS.values())
                .select_related("nutrient")
            )

            values = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0}
            for row in pn:
                usda_id = row.nutrient.usda_nutrient_id
                amount = safe_float(row.amount_per_100g)
                if usda_id == USDA_IDS["kcal"]:
                    values["kcal"] = amount
                elif usda_id == USDA_IDS["protein"]:
                    values["protein"] = amount
                elif usda_id == USDA_IDS["fat"]:
                    values["fat"] = amount
                elif usda_id == USDA_IDS["carb"]:
                    values["carb"] = amount

            tags = compute_tags(values["kcal"], values["protein"], values["fat"], values["carb"])
            props = compute_properties(values["kcal"], values["protein"], values["fat"], values["carb"])

            if dry_run:
                self.stdout.write(f"[DRY] Product #{product.id} {product.name}: tags={tags} props={props}")
                continue

            product.tags = tags
            product.properties = props
            product.save(update_fields=["tags", "properties"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated products: {updated}"))