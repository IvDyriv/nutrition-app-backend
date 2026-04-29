from decimal import Decimal
from typing import Any

from nutrition.models import UserProfile
from nutrition.services.meal_analysis import analyze_meal, quantize_decimal
from nutrition.services.norms import get_micro_norms


LOW_PERCENT_THRESHOLD = Decimal("90")
HIGH_PERCENT_THRESHOLD = Decimal("120")
PERCENT_MULTIPLIER = Decimal("100")
DECIMAL_ZERO = Decimal("0")


def get_profile_or_raise(profile_id: int) -> UserProfile:
    try:
        return UserProfile.objects.get(pk=profile_id)
    except UserProfile.DoesNotExist as exc:
        raise ValueError(f"UserProfile with id={profile_id} not found") from exc


def get_status(
    consumed: Decimal,
    recommended: Decimal,
    upper_limit: Decimal | None = None,
) -> str:
    if recommended <= DECIMAL_ZERO:
        return "unknown"

    percent = calculate_percent_of_norm(consumed, recommended)

    if upper_limit is not None and consumed > upper_limit:
        return "high"

    if percent < LOW_PERCENT_THRESHOLD:
        return "low"

    if percent > HIGH_PERCENT_THRESHOLD:
        return "high"

    return "ok"


def calculate_percent_of_norm(
    consumed: Decimal,
    recommended: Decimal,
) -> Decimal:
    if recommended <= DECIMAL_ZERO:
        return DECIMAL_ZERO

    return (consumed / recommended) * PERCENT_MULTIPLIER


def build_consumed_nutrients_map(
    nutrients: list[dict[str, Any]],
) -> dict[int, Decimal]:
    return {
        item["nutrient_id"]: Decimal(item["total_amount"])
        for item in nutrients
    }


def build_nutrient_comparison_item(
    *,
    norm,
    consumed_amount: Decimal,
) -> dict[str, Any]:
    recommended_amount = Decimal(norm.recommended_amount)
    upper_limit = Decimal(norm.upper_limit) if norm.upper_limit is not None else None
    percent_of_norm = calculate_percent_of_norm(
        consumed=consumed_amount,
        recommended=recommended_amount,
    )

    return {
        "nutrient_id": norm.nutrient.id,
        "nutrient_name": norm.nutrient.name,
        "unit": norm.nutrient.unit,
        "consumed_amount": quantize_decimal(consumed_amount),
        "recommended_amount": quantize_decimal(recommended_amount),
        "upper_limit": quantize_decimal(upper_limit) if upper_limit is not None else None,
        "percent_of_norm": quantize_decimal(percent_of_norm, "0.01"),
        "status": get_status(
            consumed=consumed_amount,
            recommended=recommended_amount,
            upper_limit=upper_limit,
        ),
    }


def build_comparison(profile: UserProfile, meal_result: dict[str, Any]) -> list[dict[str, Any]]:
    consumed_by_nutrient_id = build_consumed_nutrients_map(meal_result["nutrients"])

    seen_nutrient_ids = set()
    comparison = []

    for norm in get_micro_norms(age=profile.age, sex=profile.sex):
        if norm.nutrient_id in seen_nutrient_ids:
            continue

        seen_nutrient_ids.add(norm.nutrient_id)

        comparison.append(
            build_nutrient_comparison_item(
                norm=norm,
                consumed_amount=consumed_by_nutrient_id.get(
                    norm.nutrient_id,
                    DECIMAL_ZERO,
                ),
            )
        )

    return sorted(comparison, key=lambda item: item["nutrient_name"])


def compare_meal_with_norms(profile_id: int, products_data: list[dict]) -> dict[str, Any]:
    profile = get_profile_or_raise(profile_id)
    meal_result = analyze_meal(products_data)

    return {
        "profile_id": profile.id,
        "products": meal_result["products"],
        "macros": meal_result["macros"],
        "nutrients": meal_result["nutrients"],
        "comparison": build_comparison(profile, meal_result),
    }