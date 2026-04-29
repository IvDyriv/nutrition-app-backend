from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from nutrition.models import Product


DECIMAL_ZERO = Decimal("0")
GRAMS_IN_100G = Decimal("100")

MACRO_NUTRIENT_NAME_TO_KEY = {
    "Energy": "calories",
    "Protein": "protein_g",
    "Total lipid (fat)": "fat_g",
    "Carbohydrate, by difference": "carbs_g",
}

DEFAULT_MACROS = {
    "calories": DECIMAL_ZERO,
    "protein_g": DECIMAL_ZERO,
    "fat_g": DECIMAL_ZERO,
    "carbs_g": DECIMAL_ZERO,
}


def quantize_decimal(value: Decimal | int | float, places: str = "0.0001") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def get_active_products_by_ids(product_ids: list[int]) -> dict[int, Product]:
    products = (
        Product.objects.filter(id__in=product_ids, is_active=True)
        .prefetch_related("product_nutrients__nutrient")
    )

    return {product.id: product for product in products}


def get_product_or_raise(products_by_id: dict[int, Product], product_id: int) -> Product:
    product = products_by_id.get(product_id)

    if product is None:
        raise ValueError(f"Product with id={product_id} not found")

    return product


def build_product_result(product: Product, grams: Decimal) -> dict[str, Any]:
    return {
        "product_id": product.id,
        "product_name": product.name,
        "grams": quantize_decimal(grams, "0.01"),
    }


def calculate_product_nutrient_amount(
    amount_per_100g: Decimal,
    grams: Decimal,
) -> Decimal:
    return Decimal(amount_per_100g) * (grams / GRAMS_IN_100G)


def create_nutrient_bucket() -> dict[str, Any]:
    return {
        "nutrient_id": None,
        "nutrient_name": "",
        "unit": "",
        "total_amount": DECIMAL_ZERO,
    }


def add_product_nutrients_to_totals(
    product: Product,
    grams: Decimal,
    nutrient_totals: dict[int, dict[str, Any]],
    macros: dict[str, Decimal],
) -> None:
    for product_nutrient in product.product_nutrients.all():
        nutrient = product_nutrient.nutrient
        total_amount = calculate_product_nutrient_amount(
            amount_per_100g=product_nutrient.amount_per_100g,
            grams=grams,
        )

        bucket = nutrient_totals[nutrient.id]
        bucket["nutrient_id"] = nutrient.id
        bucket["nutrient_name"] = nutrient.name
        bucket["unit"] = nutrient.unit
        bucket["total_amount"] += total_amount

        macro_key = MACRO_NUTRIENT_NAME_TO_KEY.get(nutrient.name)
        if macro_key:
            macros[macro_key] += total_amount


def build_nutrients_response(
    nutrient_totals: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    nutrients = [
        {
            "nutrient_id": item["nutrient_id"],
            "nutrient_name": item["nutrient_name"],
            "unit": item["unit"],
            "total_amount": quantize_decimal(item["total_amount"]),
        }
        for item in nutrient_totals.values()
    ]

    return sorted(nutrients, key=lambda item: item["nutrient_name"])


def build_macros_response(macros: dict[str, Decimal]) -> dict[str, Decimal]:
    return {
        "calories": quantize_decimal(macros["calories"]),
        "protein_g": quantize_decimal(macros["protein_g"]),
        "fat_g": quantize_decimal(macros["fat_g"]),
        "carbs_g": quantize_decimal(macros["carbs_g"]),
    }


def analyze_meal(products_data: list[dict]) -> dict[str, Any]:
    product_ids = [item["product_id"] for item in products_data]
    products_by_id = get_active_products_by_ids(product_ids)

    result_products = []
    nutrient_totals = defaultdict(create_nutrient_bucket)
    macros = DEFAULT_MACROS.copy()

    for item in products_data:
        product_id = item["product_id"]
        grams = Decimal(item["grams"])
        product = get_product_or_raise(products_by_id, product_id)

        result_products.append(build_product_result(product, grams))

        add_product_nutrients_to_totals(
            product=product,
            grams=grams,
            nutrient_totals=nutrient_totals,
            macros=macros,
        )

    return {
        "products": result_products,
        "macros": build_macros_response(macros),
        "nutrients": build_nutrients_response(nutrient_totals),
    }