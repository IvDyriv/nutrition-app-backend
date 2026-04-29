from decimal import Decimal

from rest_framework import serializers

from .models import Nutrient, Product, ProductNutrient, UserProfile
from .services.products import get_product_macros_data

PRODUCT_TAG_CHOICES = [
    "lo_cal",
    "prot",
    "fat",
    "carb",
    "prot-fat",
    "prot-carb",
    "fat-carb",
    "fat-prot",
    "carb-prot",
    "carb-fat",
    "balanced",
]

PRODUCT_PROPERTY_CHOICES = [
    "hi-prot",
    "hi-fat",
    "hi-carb",
    "hi-cal",
    "low-prot",
    "low-fat",
    "low-carb",
    "low-cal",
    "fiber",
]


class NutrientInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutrient
        fields = ["id", "name", "unit"]


class ProductNutrientSerializer(serializers.ModelSerializer):
    nutrient = NutrientInlineSerializer(read_only=True)

    class Meta:
        model = ProductNutrient
        fields = ["nutrient", "amount_per_100g"]


class ProductMacrosSerializer(serializers.Serializer):
    kcal = serializers.IntegerField()
    protein = serializers.IntegerField()
    fat = serializers.IntegerField()
    carbs = serializers.IntegerField()


class ProductListSerializer(serializers.ModelSerializer):
    macros = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "category",
            "tags",
            "properties",
            "macros",
        ]

    def get_macros(self, obj: Product) -> dict[str, int]:
        return get_product_macros_data(obj)


class ProductDetailSerializer(ProductListSerializer):
    product_nutrients = ProductNutrientSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ["product_nutrients"]


class ProductListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=40)
    page = serializers.IntegerField(required=False, min_value=1)
    tag = serializers.ChoiceField(required=False, choices=PRODUCT_TAG_CHOICES)
    prop = serializers.ListField(
        child=serializers.ChoiceField(choices=PRODUCT_PROPERTY_CHOICES),
        required=False,
    )

    def validate_search(self, value: str) -> str:
        cleaned_value = value.replace(" ", "").replace("-", "")

        if not cleaned_value.isalnum():
            raise serializers.ValidationError("Invalid search value.")

        return value


class ProductSummaryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    cal = serializers.IntegerField()
    prot = serializers.IntegerField()
    fat = serializers.IntegerField()
    carb = serializers.IntegerField()
    tag = serializers.CharField(allow_null=True)
    properties = serializers.ListField(
        child=serializers.CharField(),
        default=list,
    )


class ProductSummaryResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    items = ProductSummaryItemSerializer(many=True)


class ProductTagsSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField())
    properties = serializers.ListField(child=serializers.CharField())


class NormsInputSerializer(serializers.Serializer):
    age = serializers.IntegerField(min_value=1, max_value=120)
    sex = serializers.ChoiceField(choices=["male", "female", "na"])
    height_cm = serializers.DecimalField(max_digits=6, decimal_places=2)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2)
    body_fat_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    activity = serializers.ChoiceField(
        choices=["static", "mild", "moderate", "high", "exhausting"],
    )
    goal = serializers.ChoiceField(
        choices=["maintenance", "cut", "bulk"],
        default="maintenance",
        required=False,
    )


class MacroTargetsSerializer(serializers.Serializer):
    calories = serializers.DecimalField(max_digits=10, decimal_places=2)
    protein_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    fat_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    carbs_g = serializers.DecimalField(max_digits=10, decimal_places=2)


class MicroNormItemSerializer(serializers.Serializer):
    nutrient_id = serializers.IntegerField()
    nutrient_name = serializers.CharField()
    unit = serializers.CharField()
    recommended_amount = serializers.DecimalField(max_digits=10, decimal_places=4)
    upper_limit = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        allow_null=True,
    )
    source = serializers.CharField()
    note = serializers.CharField()


class NormsResponseSerializer(serializers.Serializer):
    bmi = serializers.DecimalField(max_digits=10, decimal_places=2)
    bmr = serializers.DecimalField(max_digits=10, decimal_places=2)
    tdee = serializers.DecimalField(max_digits=10, decimal_places=2)
    macro_targets = MacroTargetsSerializer()
    micro_targets = MicroNormItemSerializer(many=True)


class MealProductInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    grams = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )


class AnalyzeMealInputSerializer(serializers.Serializer):
    products = MealProductInputSerializer(many=True)


class MealProductResultSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    grams = serializers.DecimalField(max_digits=8, decimal_places=2)


class NutrientTotalSerializer(serializers.Serializer):
    nutrient_id = serializers.IntegerField()
    nutrient_name = serializers.CharField()
    unit = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=4)


class MacroSummarySerializer(serializers.Serializer):
    calories = serializers.DecimalField(max_digits=12, decimal_places=4)
    protein_g = serializers.DecimalField(max_digits=12, decimal_places=4)
    fat_g = serializers.DecimalField(max_digits=12, decimal_places=4)
    carbs_g = serializers.DecimalField(max_digits=12, decimal_places=4)


class AnalyzeMealResponseSerializer(serializers.Serializer):
    products = MealProductResultSerializer(many=True)
    macros = MacroSummarySerializer()
    nutrients = NutrientTotalSerializer(many=True)


class CompareWithNormsInputSerializer(serializers.Serializer):
    profile_id = serializers.IntegerField(min_value=1)
    products = MealProductInputSerializer(many=True)


class NutrientComparisonSerializer(serializers.Serializer):
    nutrient_id = serializers.IntegerField()
    nutrient_name = serializers.CharField()
    unit = serializers.CharField()
    consumed_amount = serializers.DecimalField(max_digits=12, decimal_places=4)
    recommended_amount = serializers.DecimalField(max_digits=12, decimal_places=4)
    upper_limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        allow_null=True,
        required=False,
    )
    percent_of_norm = serializers.DecimalField(max_digits=8, decimal_places=2)
    status = serializers.CharField()


class CompareWithNormsResponseSerializer(serializers.Serializer):
    profile_id = serializers.IntegerField()
    products = MealProductResultSerializer(many=True)
    macros = MacroSummarySerializer()
    nutrients = NutrientTotalSerializer(many=True)
    comparison = NutrientComparisonSerializer(many=True)


class ProductMicroSerializer(serializers.Serializer):
    name = serializers.CharField()
    unit = serializers.CharField()
    amount = serializers.IntegerField()


class ProductBatchDetailResponseSerializer(serializers.Serializer):
    item = ProductSummaryItemSerializer(allow_null=True)
    micro = ProductMicroSerializer(many=True)


class ProductBatchRequestSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'age',
            'sex',
            'height_cm',
            'weight_kg',
            'body_fat_percent',
            'activity',
            'goal',
        ]

    def validate_age(self, value):
        if value < 1 or value > 120:
            raise serializers.ValidationError("Age must be between 1 and 120.")
        return value

    def validate_height_cm(self, value):
        if value < 50 or value > 300:
            raise serializers.ValidationError("Height must be between 50 and 300 cm.")
        return value

    def validate_weight_kg(self, value):
        if value < 3 or value > 500:
            raise serializers.ValidationError("Weight must be between 3 and 500 kg.")
        return value

    def validate_body_fat_percent(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                "Body fat percentage must be between 0 and 100."
            )
        return value

    def validate(self, data):
        if data.get("activity") == "exhausting" and data.get("weight_kg", 0) < 30:
            raise serializers.ValidationError(
                "Weight must be sufficient for exhaustive activity."
            )
        return data