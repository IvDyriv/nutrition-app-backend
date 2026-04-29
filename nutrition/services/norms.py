from decimal import Decimal, ROUND_HALF_UP
from typing import Final

from nutrition.models import NutrientNorm


DEFAULT_DECIMAL_PLACES: Final[str] = "0.01"

BMR_WEIGHT_COEFFICIENT: Final[Decimal] = Decimal("10")
BMR_HEIGHT_COEFFICIENT: Final[Decimal] = Decimal("6.25")
BMR_AGE_COEFFICIENT: Final[Decimal] = Decimal("5")

KATCH_BASE_VALUE: Final[Decimal] = Decimal("370")
KATCH_LEAN_MASS_COEFFICIENT: Final[Decimal] = Decimal("21.6")

PERCENT: Final[Decimal] = Decimal("100")
BMI_OBESITY_THRESHOLD: Final[Decimal] = Decimal("30")

CALORIES_PER_GRAM_PROTEIN: Final[Decimal] = Decimal("4")
CALORIES_PER_GRAM_CARBS: Final[Decimal] = Decimal("4")
CALORIES_PER_GRAM_FAT: Final[Decimal] = Decimal("9")

GOAL_CALORIE_ADJUSTMENT: Final[dict[str, Decimal]] = {
    "cut": Decimal("-300"),
    "maintenance": Decimal("0"),
    "bulk": Decimal("300"),
}

GOAL_MACRO_RATIOS: Final[dict[str, dict[str, Decimal]]] = {
    "cut": {
        "protein": Decimal("0.30"),
        "fat": Decimal("0.25"),
    },
    "maintenance": {
        "protein": Decimal("0.25"),
        "fat": Decimal("0.25"),
    },
    "bulk": {
        "protein": Decimal("0.25"),
        "fat": Decimal("0.25"),
    },
}

MIFFLIN_SEX_SUFFIX: Final[dict[str, Decimal]] = {
    "male": Decimal("5"),
    "female": Decimal("-161"),
    "na": Decimal("-78"),
}

ACTIVITY_MULTIPLIERS: Final[dict[str, Decimal]] = {
    "static": Decimal("1.2"),
    "mild": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
    "exhausting": Decimal("1.9"),
}

ATHLETE_THRESHOLDS: Final[dict[str, dict[str, Decimal]]] = {
    "male": {
        "athlete_fat": Decimal("18"),
        "max_fat": Decimal("25"),
        "min_bmi": Decimal("25"),
        "athlete_bmi": Decimal("28"),
        "lean_cap": Decimal("0.5"),
    },
    "female": {
        "athlete_fat": Decimal("22"),
        "max_fat": Decimal("30"),
        "min_bmi": Decimal("20"),
        "athlete_bmi": Decimal("24"),
        "lean_cap": Decimal("0.8"),
    },
    "na": {
        "athlete_fat": Decimal("20"),
        "max_fat": Decimal("27"),
        "min_bmi": Decimal("22"),
        "athlete_bmi": Decimal("26"),
        "lean_cap": Decimal("0.65"),
    },
}


def q(value: Decimal | float | int, places: str = DEFAULT_DECIMAL_PLACES) -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def get_required_mapping_value(
    mapping: dict[str, Decimal],
    key: str,
    field_name: str,
) -> Decimal:
    try:
        return mapping[key]
    except KeyError as exc:
        raise ValueError(f"Invalid {field_name}: {key}") from exc


def calculate_mifflin_bmr(
    weight: Decimal,
    height: Decimal,
    sex: str,
    age: int,
) -> Decimal:
    sex_suffix = get_required_mapping_value(MIFFLIN_SEX_SUFFIX, sex, "sex")

    return (
        BMR_WEIGHT_COEFFICIENT * weight
        + BMR_HEIGHT_COEFFICIENT * height
        - BMR_AGE_COEFFICIENT * Decimal(age)
        + sex_suffix
    )


def calculate_katch_mcardle_bmr(
    weight: Decimal,
    body_fat_percent: Decimal,
) -> Decimal:
    lean_mass = weight * (PERCENT - body_fat_percent) / PERCENT
    return KATCH_BASE_VALUE + KATCH_LEAN_MASS_COEFFICIENT * lean_mass


def calc_bmi(weight: Decimal, height_cm: Decimal) -> Decimal:
    height_m = height_cm / Decimal("100")
    return weight / (height_m**2)


def get_athlete_score(
    bmi: Decimal,
    body_fat_percent: Decimal,
    sex: str,
) -> Decimal:
    thresholds = ATHLETE_THRESHOLDS.get(sex)

    if thresholds is None:
        raise ValueError(f"Invalid sex: {sex}")

    athlete_fat = thresholds["athlete_fat"]
    max_fat = thresholds["max_fat"]
    min_bmi = thresholds["min_bmi"]
    athlete_bmi = thresholds["athlete_bmi"]
    lean_cap = thresholds["lean_cap"]

    if body_fat_percent >= max_fat:
        return Decimal("0")

    body_fat_score = max(
        Decimal("0"),
        (max_fat - body_fat_percent) / (max_fat - athlete_fat),
    )

    if bmi >= BMI_OBESITY_THRESHOLD:
        if body_fat_percent <= athlete_fat:
            return Decimal("1")

        return Decimal("0")

    if bmi < min_bmi:
        return min(Decimal("1"), body_fat_score * lean_cap)

    bmi_score = min(
        Decimal("1"),
        lean_cap
        + (
            (Decimal("1") - lean_cap)
            * (bmi - min_bmi)
            / (athlete_bmi - min_bmi)
        ),
    )

    return min(Decimal("1"), body_fat_score * bmi_score)


def calculate_bmr(
    *,
    weight: Decimal,
    height: Decimal,
    sex: str,
    age: int,
    body_fat_percent: Decimal | None = None,
) -> Decimal:
    mifflin_bmr = calculate_mifflin_bmr(
        weight=weight,
        height=height,
        sex=sex,
        age=age,
    )

    if body_fat_percent is None:
        return q(mifflin_bmr)

    bmi = calc_bmi(weight, height)
    athlete_coefficient = get_athlete_score(
        bmi=bmi,
        body_fat_percent=body_fat_percent,
        sex=sex,
    )
    katch_mcardle_bmr = calculate_katch_mcardle_bmr(weight, body_fat_percent)

    result = (
        mifflin_bmr * (Decimal("1") - athlete_coefficient)
        + katch_mcardle_bmr * athlete_coefficient
    )

    return q(result)


def calculate_tdee(
    *,
    weight: Decimal,
    height: Decimal,
    sex: str,
    age: int,
    activity: str,
    body_fat_percent: Decimal | None = None,
) -> Decimal:
    activity_multiplier = get_required_mapping_value(
        ACTIVITY_MULTIPLIERS,
        activity,
        "activity",
    )
    bmr = calculate_bmr(
        weight=weight,
        height=height,
        sex=sex,
        age=age,
        body_fat_percent=body_fat_percent,
    )

    return q(bmr * activity_multiplier)


def calculate_macro_targets(tdee: Decimal, goal: str) -> dict[str, Decimal]:
    calorie_adjustment = get_required_mapping_value(
        GOAL_CALORIE_ADJUSTMENT,
        goal,
        "goal",
    )
    macro_ratios = GOAL_MACRO_RATIOS.get(goal)

    if macro_ratios is None:
        raise ValueError(f"Invalid goal: {goal}")

    target_calories = tdee + calorie_adjustment

    protein_calories = target_calories * macro_ratios["protein"]
    fat_calories = target_calories * macro_ratios["fat"]
    carbs_calories = target_calories - protein_calories - fat_calories

    return {
        "calories": q(target_calories),
        "protein_g": q(protein_calories / CALORIES_PER_GRAM_PROTEIN),
        "fat_g": q(fat_calories / CALORIES_PER_GRAM_FAT),
        "carbs_g": q(carbs_calories / CALORIES_PER_GRAM_CARBS),
    }


def get_micro_norms(*, age: int, sex: str):
    return (
        NutrientNorm.objects.filter(
            age_min__lte=age,
            age_max__gte=age,
            sex__in=[sex, "na"],
        )
        .select_related("nutrient")
        .order_by("nutrient__name", "sex")
    )


def build_micro_targets(*, age: int, sex: str) -> list[dict]:
    seen_nutrient_ids = set()
    micro_targets = []

    for norm in get_micro_norms(age=age, sex=sex):
        if norm.nutrient_id in seen_nutrient_ids:
            continue

        seen_nutrient_ids.add(norm.nutrient_id)
        micro_targets.append(
            {
                "nutrient_id": norm.nutrient.id,
                "nutrient_name": norm.nutrient.name,
                "unit": norm.nutrient.unit,
                "recommended_amount": norm.recommended_amount,
                "upper_limit": norm.upper_limit,
                "source": norm.source,
                "note": norm.note,
            }
        )

    return micro_targets


def calculate_norms_response(data: dict) -> dict:
    bmi = q(calc_bmi(data["weight_kg"], data["height_cm"]))
    bmr = calculate_bmr(
        weight=data["weight_kg"],
        height=data["height_cm"],
        sex=data["sex"],
        age=data["age"],
        body_fat_percent=data.get("body_fat_percent"),
    )
    tdee = calculate_tdee(
        weight=data["weight_kg"],
        height=data["height_cm"],
        sex=data["sex"],
        age=data["age"],
        activity=data["activity"],
        body_fat_percent=data.get("body_fat_percent"),
    )

    return {
        "bmi": bmi,
        "bmr": bmr,
        "tdee": tdee,
        "macro_targets": calculate_macro_targets(
            tdee,
            data.get("goal", "maintenance"),
        ),
        "micro_targets": build_micro_targets(
            age=data["age"],
            sex=data["sex"],
        ),
    }
