from decimal import Decimal

from django.db.models import QuerySet

from nutrition.models import Product


USDA_CALORIES_ID = 1008
USDA_PROTEIN_ID = 1003
USDA_FAT_ID = 1004
USDA_CARBS_ID = 1005

MACRO_NUTRIENT_IDS = {
    USDA_CALORIES_ID,
    USDA_PROTEIN_ID,
    USDA_FAT_ID,
    USDA_CARBS_ID,
}

MACRO_NUTRIENT_ID_TO_KEY = {
    USDA_CALORIES_ID: "kcal",
    USDA_PROTEIN_ID: "protein",
    USDA_FAT_ID: "fat",
    USDA_CARBS_ID: "carbs",
}


def get_active_products_queryset() -> QuerySet[Product]:
    return (
        Product.objects.filter(is_active=True)
        .prefetch_related("product_nutrients__nutrient")
    )


def filter_products_by_tag_and_properties(
    queryset: QuerySet[Product],
    *,
    tag: str | None,
    properties: list[str],
) -> QuerySet[Product]:
    if tag:
        queryset = queryset.filter(tags__contains=[tag])

    if properties:
        queryset = queryset.filter(properties__overlap=properties)

    return queryset


def get_product_macros_data(product: Product) -> dict[str, int]:
    macros = {
        "kcal": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
    }

    for product_nutrient in product.product_nutrients.all():
        nutrient_id = product_nutrient.nutrient.usda_nutrient_id
        macro_key = MACRO_NUTRIENT_ID_TO_KEY.get(nutrient_id)

        if macro_key:
            amount = product_nutrient.amount_per_100g or Decimal("0")
            macros[macro_key] = int(round(amount))

    return macros


def build_product_summary(product: Product) -> dict:
    macros = get_product_macros_data(product)

    return {
        "id": product.id,
        "name": product.name,
        "cal": int(round(macros.get("kcal", 0))),
        "prot": int(round(macros.get("protein", 0))),
        "fat": int(round(macros.get("fat", 0))),
        "carb": int(round(macros.get("carbs", 0))),
        "tag": product.tags[0] if product.tags else None,
        "properties": product.properties or [],
    }


def build_product_detail(product: Product) -> dict:
    micro = []

    for product_nutrient in product.product_nutrients.all():
        nutrient = product_nutrient.nutrient

        if nutrient.usda_nutrient_id in MACRO_NUTRIENT_IDS:
            continue

        amount = product_nutrient.amount_per_100g or 0

        micro.append(
            {
                "name": nutrient.name,
                "unit": nutrient.unit,
                "amount": int(round(float(amount))),
            }
        )

    return {
        "item": build_product_summary(product),
        "micro": micro,
    }


def get_available_product_tags_and_properties() -> dict[str, list[str]]:
    tags = set()
    properties = set()

    for product in Product.objects.only("tags", "properties"):
        tags.update(product.tags or [])
        properties.update(product.properties or [])

    return {
        "tags": sorted(tags),
        "properties": sorted(properties),
    }


def get_products_by_ids(product_ids: list[int]) -> dict[int, Product]:
    products = get_active_products_queryset().filter(id__in=product_ids)
    return {product.id: product for product in products}
