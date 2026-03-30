from django.core.management.base import BaseCommand
from django.db import transaction

from nutrition.models import Product, ProductNutrient


USDA_IDS = {
    "kcal": 1008,
    "protein": 1003,
    "fat": 1004,
    "carb": 1005,
    "fiber": 1079,
}


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def compute_tag(kcal, protein_g, fat_g, carb_g):

    if kcal < 60:
        return "lo_cal"

    protein_kcal = protein_g * 4.0
    carb_kcal = carb_g * 4.0
    fat_kcal = fat_g * 9.0

    if kcal <= 0:
        return "balanced"

    if protein_kcal > 0.60 * kcal:
        return "prot"
    if carb_kcal > 0.60 * kcal:
        return "carb"
    if fat_kcal > 0.60 * kcal:
        return "fat"

    if protein_kcal > 0.40 * kcal and fat_kcal > 0.25 * kcal:
        return "prot-fat"

    if protein_kcal > 0.40 * kcal and carb_kcal > 0.25 * kcal:
        return "prot-carb"

    if fat_kcal > 0.40 * kcal and protein_kcal > 0.25 * kcal:
        return "fat-prot"

    if fat_kcal > 0.40 * kcal and carb_kcal > 0.25 * kcal:
        return "fat-carb"

    if carb_kcal > 0.40 * kcal and protein_kcal > 0.25 * kcal:
        return "carb-prot"

    if carb_kcal > 0.40 * kcal and fat_kcal > 0.25 * kcal:
        return "carb-fat"

    return "balanced"


def compute_properties(kcal, protein_g, fat_g, carb_g, fiber_g):

    props = []

    if protein_g > 15:
        props.append("hi-prot")
    if fat_g > 15:
        props.append("hi-fat")
    if carb_g > 40:
        props.append("hi-carb")
    if kcal > 200:
        props.append("hi-cal")

    if protein_g < 5:
        props.append("low-prot")
    if fat_g < 3:
        props.append("low-fat")
    if carb_g < 5:
        props.append("low-carb")
    if kcal < 100:
        props.append("low-cal")
    if fiber_g > 5:
        props.append("fiber")

    return props


class Command(BaseCommand):
    help = "Compute tags and property tags for products based on ProductNutrient amounts per 100g."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Update only products with empty tags/properties",
        )

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

            values = {
                "kcal": 0.0,
                "protein": 0.0,
                "fat": 0.0,
                "carb": 0.0,
                "fiber": 0.0,
            }

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
                elif usda_id == USDA_IDS["fiber"]:
                    values["fiber"] = amount

            tag = compute_tag(
                values["kcal"],
                values["protein"],
                values["fat"],values["carb"],
            )

            props = compute_properties(
                values["kcal"],
                values["protein"],
                values["fat"],
                values["carb"],
                values["fiber"],
            )

            if dry_run:
                self.stdout.write(
                    f"[DRY] Product #{product.id} {product.name}: "
                    f"tag={tag} props={props}"
                )
                continue

            product.tags = [tag]
            product.properties = props
            product.save(update_fields=["tags", "properties"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated products: {updated}"))