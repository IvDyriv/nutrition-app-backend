from decimal import Decimal, ROUND_HALF_UP

from nutrition.models import UserProfile
from nutrition.services.meal_analysis import analyze_meal
from nutrition.services.norms import get_micro_norms


def q(value: Decimal | int | float, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def get_status(consumed: Decimal, recommended: Decimal, upper_limit: Decimal | None = None) -> str:
    if recommended <= 0:
        return "unknown"

    percent = (consumed / recommended) * Decimal("100")

    if upper_limit is not None and consumed > upper_limit:
        return "high"

    if percent < Decimal("90"):
        return "low"

    if percent > Decimal("120"):
        return "high"

    return "ok"


def compare_meal_with_norms(profile_id: int, products_data: list[dict]) -> dict:
    try:
        profile = UserProfile.objects.get(pk=profile_id)
    except UserProfile.DoesNotExist:
        raise ValueError(f"UserProfile with id={profile_id} not found")

    meal_result = analyze_meal(products_data)

    consumed_by_name_unit = {}
    for item in meal_result["nutrients"]:
        key = (item["nutrient_name"], item["unit"])
        consumed_by_name_unit[key] = Decimal(item["total_amount"])

    norms_qs = get_micro_norms(age=profile.age, sex=profile.sex)

    seen_nutrients = set()
    comparison = []

    for norm in norms_qs:
        if norm.nutrient_id in seen_nutrients:
            continue
        seen_nutrients.add(norm.nutrient_id)

        key = (norm.nutrient.name, norm.nutrient.unit)
        consumed_amount = consumed_by_name_unit.get(key, Decimal("0"))
        recommended_amount = Decimal(norm.recommended_amount)
        upper_limit = Decimal(norm.upper_limit) if norm.upper_limit is not None else None

        percent_of_norm = Decimal("0")
        if recommended_amount > 0:
            percent_of_norm = (consumed_amount / recommended_amount) * Decimal("100")

        comparison.append({
            "nutrient_id": norm.nutrient.id,
            "nutrient_name": norm.nutrient.name,
            "unit": norm.nutrient.unit,
            "consumed_amount": consumed_amount.quantize(Decimal("0.0001")),
            "recommended_amount": recommended_amount.quantize(Decimal("0.0001")),
            "upper_limit": upper_limit.quantize(Decimal("0.0001")) if upper_limit is not None else None,
            "percent_of_norm": q(percent_of_norm),
            "status": get_status(consumed_amount, recommended_amount, upper_limit),
        })

    comparison.sort(key=lambda x: x["nutrient_name"])

    return {
        "profile_id": profile.id,
        "products": meal_result["products"],
        "macros": meal_result["macros"],
        "nutrients": meal_result["nutrients"],
        "comparison": comparison,
    }
