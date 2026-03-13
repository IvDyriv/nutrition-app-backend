from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from nutrition.models import Product


def q(value: Decimal | int | float, places: str = "0.0001") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


MACRO_NAME_MAP = {
    "Energy": "calories",
    "Protein": "protein_g",
    "Total lipid (fat)": "fat_g",
    "Carbohydrate, by difference": "carbs_g",
}


def analyze_meal(products_data: list[dict]) -> dict:
    product_ids = [item["product_id"] for item in products_data]

    products_qs = Product.objects.filter(
        id__in=product_ids,
        is_active=True,
    ).prefetch_related("product_nutrients__nutrient")

    products_by_id = {product.id: product for product in products_qs}

    result_products = []
    nutrient_totals = defaultdict(lambda: {
        "nutrient_id": None,
        "nutrient_name": "",
        "unit": "",
        "total_amount": Decimal("0"),
    })

    macros = {
        "calories": Decimal("0"),
        "protein_g": Decimal("0"),
        "fat_g": Decimal("0"),
        "carbs_g": Decimal("0"),
    }

    for item in products_data:
        product_id = item["product_id"]
        grams = Decimal(item["grams"])

        product = products_by_id.get(product_id)
        if not product:
            raise ValueError(f"Product with id={product_id} not found")

        result_products.append({
            "product_id": product.id,
            "product_name": product.name,
            "grams": q(grams, "0.01"),
        })

        ratio = grams / Decimal("100")

        for pn in product.product_nutrients.all():
            total_amount = Decimal(pn.amount_per_100g) * ratio
            nutrient = pn.nutrient

            bucket = nutrient_totals[nutrient.id]
            bucket["nutrient_id"] = nutrient.id
            bucket["nutrient_name"] = nutrient.name
            bucket["unit"] = nutrient.unit
            bucket["total_amount"] += total_amount

            macro_key = MACRO_NAME_MAP.get(nutrient.name)
            if macro_key:
                macros[macro_key] += total_amount

    nutrients_list = []
    for item in nutrient_totals.values():
        nutrients_list.append({
            "nutrient_id": item["nutrient_id"],
            "nutrient_name": item["nutrient_name"],
            "unit": item["unit"],
            "total_amount": q(item["total_amount"]),
        })

    nutrients_list.sort(key=lambda x: x["nutrient_name"])

    return {
        "products": result_products,
        "macros": {
            "calories": q(macros["calories"]),
            "protein_g": q(macros["protein_g"]),
            "fat_g": q(macros["fat_g"]),
            "carbs_g": q(macros["carbs_g"]),
        },
        "nutrients": nutrients_list,
    }