from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from decimal import Decimal


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Product(TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    usda_fdc_id = models.IntegerField(null=True, blank=True, unique=True)
    data_source = models.CharField(max_length=50, default="USDA")

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

    tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    properties = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )

    class Meta:
        indexes = [
            GinIndex(fields=["tags"], name="product_tags_gin"),
            GinIndex(fields=["properties"], name="product_props_gin"),
        ]

    def __str__(self) -> str:
        return self.name


class Nutrient(TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    unit = models.CharField(max_length=20)

    usda_nutrient_id = models.IntegerField(null=True, blank=True, unique=True)

    is_macro = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "unit"], name="uniq_nutrient_name_unit")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class ProductNutrient(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_nutrients")
    nutrient = models.ForeignKey(Nutrient, on_delete=models.PROTECT, related_name="product_nutrients")

    amount_per_100g = models.DecimalField(max_digits=12, decimal_places=4)

    data_source = models.CharField(max_length=50, default="USDA")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "nutrient"], name="uniq_product_nutrient"),
            models.CheckConstraint(
                condition=models.Q(amount_per_100g__gte=0),
                name="chk_amount_per_100g_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} - {self.nutrient_id}: {self.amount_per_100g} per 100g"


class SexChoices(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    NA = "na", "N/A"


class ActivityChoices(models.TextChoices):
    STATIC = "static", "Static"
    MILD = "mild", "Mild"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"
    EXHAUSTING = "exhausting", "Exhausting"


class GoalChoices(models.TextChoices):
    MAINTENANCE = "maintenance", "Maintenance"
    CUT = "cut", "Cut"
    BULK = "bulk", "Bulk"


class UserProfile(TimeStampedModel):
    age = models.PositiveIntegerField()
    sex = models.CharField(
        max_length=10,
        choices=SexChoices.choices,
        default=SexChoices.NA,
    )
    height_cm = models.DecimalField(max_digits=6, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    body_fat_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    activity = models.CharField(
        max_length=20,
        choices=ActivityChoices.choices,
        default=ActivityChoices.MODERATE,
    )
    goal = models.CharField(
        max_length=20,
        choices=GoalChoices.choices,
        default=GoalChoices.MAINTENANCE,
    )

    class Meta:
        indexes = [
            models.Index(fields=["sex", "age"]),
        ]

    def __str__(self) -> str:
        return f"{self.sex} / {self.age}y / {self.weight_kg}kg"


class NutrientNorm(TimeStampedModel):
    nutrient = models.ForeignKey(
        Nutrient,
        on_delete=models.CASCADE,
        related_name="norms",
    )
    sex = models.CharField(
        max_length=10,
        choices=SexChoices.choices,
        default=SexChoices.NA,
    )
    age_min = models.PositiveIntegerField()
    age_max = models.PositiveIntegerField()

    recommended_amount = models.DecimalField(max_digits=10, decimal_places=4)
    upper_limit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )

    source = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["sex", "age_min", "age_max"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age_min__gte=0),
                name="norm_age_min_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(age_max__gte=0),
                name="norm_age_max_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_amount__gte=0),
                name="norm_recommended_amount_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nutrient.name} / {self.sex} / {self.age_min}-{self.age_max}"


from django.contrib.postgres.fields import ArrayField


class DietTypeChoices(models.TextChoices):
    OMNIVORE = "omnivore", "Omnivore"
    VEGETARIAN = "vegetarian", "Vegetarian"
    VEGAN = "vegan", "Vegan"
    KETO = "keto", "Keto"
    HIGH_PROTEIN = "high_protein", "High protein"


class MealTypeChoices(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    DINNER = "dinner", "Dinner"
    SNACK = "snack", "Snack"


class UserPreferences(TimeStampedModel):
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    diet_type = models.CharField(
        max_length=20,
        choices=DietTypeChoices.choices,
        default=DietTypeChoices.OMNIVORE,
    )

    preferred_tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    excluded_tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )

    preferred_properties = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    excluded_properties = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            GinIndex(fields=["preferred_tags"], name="pref_tags_gin"),
            GinIndex(fields=["excluded_tags"], name="excl_tags_gin"),
            GinIndex(fields=["preferred_properties"], name="pref_props_gin"),
            GinIndex(fields=["excluded_properties"], name="excl_props_gin"),
        ]

    def __str__(self) -> str:
        return f"Preferences for profile #{self.user_profile_id}"


class MealLog(TimeStampedModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="meal_logs",
    )
    meal_type = models.CharField(
        max_length=20,
        choices=MealTypeChoices.choices,
        default=MealTypeChoices.LUNCH,
    )
    logged_at = models.DateTimeField()

    class Meta:
        ordering = ["-logged_at"]
        indexes = [
            models.Index(fields=["user_profile", "logged_at"]),
            models.Index(fields=["meal_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_profile_id} / {self.meal_type} / {self.logged_at}"


class MealLogItem(TimeStampedModel):
    meal_log = models.ForeignKey(
        MealLog,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="meal_log_items",
    )
    grams = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["meal_log"]),
            models.Index(fields=["product"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grams__gt=0),
                name="meal_log_item_grams_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} / {self.grams}g"



class MealTypeChoices(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    DINNER = "dinner", "Dinner"
    SNACK = "snack", "Snack"


class UserPreferences(TimeStampedModel):
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    diet_type = models.CharField(
        max_length=20,
        choices=DietTypeChoices.choices,
        default=DietTypeChoices.OMNIVORE,
    )

    preferred_tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    excluded_tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )

    preferred_properties = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    excluded_properties = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            GinIndex(fields=["preferred_tags"], name="pref_tags_gin"),
            GinIndex(fields=["excluded_tags"], name="excl_tags_gin"),
            GinIndex(fields=["preferred_properties"], name="pref_props_gin"),
            GinIndex(fields=["excluded_properties"], name="excl_props_gin"),
        ]

    def __str__(self) -> str:
        return f"Preferences for profile #{self.user_profile_id}"


class MealLog(TimeStampedModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="meal_logs",
    )
    meal_type = models.CharField(
        max_length=20,
        choices=MealTypeChoices.choices,
        default=MealTypeChoices.LUNCH,
    )
    logged_at = models.DateTimeField()

    class Meta:
        ordering = ["-logged_at"]
        indexes = [
            models.Index(fields=["user_profile", "logged_at"]),
            models.Index(fields=["meal_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_profile_id} / {self.meal_type} / {self.logged_at}"


class MealLogItem(TimeStampedModel):
    meal_log = models.ForeignKey(
        MealLog,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="meal_log_items",
    )
    grams = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["meal_log"]),
            models.Index(fields=["product"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grams__gt=0),
                name="meal_log_item_grams_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} / {self.grams}g"


