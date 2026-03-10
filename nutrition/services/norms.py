from decimal import Decimal, ROUND_HALF_UP

from nutrition.models import NutrientNorm


MAFFLIN_SUFFIX = {
    "male": Decimal("5"),
    "female": Decimal("-161"),
    "na": Decimal("-78"),
}

ACTIVITY_MULTIPLIERS = {
    "static": Decimal("1.2"),
    "mild": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
    "exhausting": Decimal("1.9"),
}

ATHLETE_THRESHOLDS = {
    "male": {
        "athleteFat": Decimal("18"),
        "maxFat": Decimal("25"),
        "minBmi": Decimal("25"),
        "athleteBmi": Decimal("28"),
        "leanCap": Decimal("0.5"),
    },
    "female": {
        "athleteFat": Decimal("22"),
        "maxFat": Decimal("30"),
        "minBmi": Decimal("20"),
        "athleteBmi": Decimal("24"),
        "leanCap": Decimal("0.8"),
    },
    "na": {
        "athleteFat": Decimal("20"),
        "maxFat": Decimal("27"),
        "minBmi": Decimal("22"),
        "athleteBmi": Decimal("26"),
        "leanCap": Decimal("0.65"),
    },
}


def q(value: Decimal | float | int, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def mifflin(weight: Decimal, height: Decimal, sex: str, age: int) -> Decimal:
    return Decimal("10") * weight + Decimal("6.25") * height - Decimal("5") * Decimal(age) + MAFFLIN_SUFFIX[sex]


def katch_mcardle(weight: Decimal, body_fat_percent: Decimal) -> Decimal:
    lean_mass = weight * (Decimal("100") - body_fat_percent) / Decimal("100")
    return Decimal("370") + Decimal("21.6") * lean_mass


def calc_bmi(weight: Decimal, height_cm: Decimal) -> Decimal:
    height_m = height_cm / Decimal("100")
    return weight / (height_m ** 2)


def get_athlete_score(bmi: Decimal, body_fat_percent: Decimal, sex: str) -> Decimal:
    thresholds = ATHLETE_THRESHOLDS[sex]

    athlete_fat = thresholds["athleteFat"]
    max_fat = thresholds["maxFat"]
    min_bmi = thresholds["minBmi"]
    athlete_bmi = thresholds["athleteBmi"]
    lean_cap = thresholds["leanCap"]

    if body_fat_percent >= max_fat:
        return Decimal("0")

    bfat_score = max(
        Decimal("0"),
        (max_fat - body_fat_percent) / (max_fat - athlete_fat),
    )

    if bmi >= Decimal("30"):
        if body_fat_percent <= athlete_fat:
            return Decimal("1")
        return Decimal("0")

    if bmi < min_bmi:
        return min(Decimal("1"), bfat_score * lean_cap)

    bmi_score = min(
        Decimal("1"),
        lean_cap + ((Decimal("1") - lean_cap) * (bmi - min_bmi) / (athlete_bmi - min_bmi)),
    )

    return min(Decimal("1"), bfat_score * bmi_score)


def calculate_bmr(
    *,
    weight: Decimal,
    height: Decimal,
    sex: str,
    age: int,
    body_fat_percent: Decimal | None = None,
) -> Decimal:
    mifflin_bmr = mifflin(weight, height, sex, age)

    if body_fat_percent is None:
        return q(mifflin_bmr)

    bmi = calc_bmi(weight, height)
    athlete_coeff = get_athlete_score(bmi, body_fat_percent, sex)
    mc_ardle_bmr = katch_mcardle(weight, body_fat_percent)

    result = mifflin_bmr * (Decimal("1") - athlete_coeff) + mc_ardle_bmr * athlete_coeff
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
    bmr = calculate_bmr(
        weight=weight,
        height=height,
        sex=sex,
        age=age,
        body_fat_percent=body_fat_percent,
    )
    return q(bmr * ACTIVITY_MULTIPLIERS[activity])


def calculate_macro_targets(tdee: Decimal, goal: str) -> dict:
    if goal == "cut":
        target_kcal = tdee - Decimal("300")
        protein_ratio = Decimal("0.30")
        fat_ratio = Decimal("0.25")
    elif goal == "bulk":
        target_kcal = tdee + Decimal("300")
        protein_ratio = Decimal("0.25")
        fat_ratio = Decimal("0.25")
    else:
        target_kcal = tdee
        protein_ratio = Decimal("0.25")
        fat_ratio = Decimal("0.25")

    protein_kcal = target_kcal * protein_ratio
    fat_kcal = target_kcal * fat_ratio
    carb_kcal = target_kcal - protein_kcal - fat_kcal

    return {
        "calories": q(target_kcal),
        "protein_g": q(protein_kcal / Decimal("4")),
        "fat_g": q(fat_kcal / Decimal("9")),
        "carbs_g": q(carb_kcal / Decimal("4")),
    }


def get_micro_norms(*, age: int, sex: str):
    return NutrientNorm.objects.filter(
        age_min__lte=age,
        age_max__gte=age,
        sex__in=[sex, "na"],
    ).select_related("nutrient").order_by("nutrient__name", "sex")