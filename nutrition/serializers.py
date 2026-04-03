from rest_framework import serializers
from .models import Product, Nutrient, ProductNutrient


def get_product_macros_data(product):
    kcal = 0
    protein = 0
    fat = 0
    carbs = 0

    for item in product.product_nutrients.all():
        nutrient_id = item.nutrient.usda_nutrient_id
        amount = item.amount_per_100g or 0

        if nutrient_id == 1008:
            kcal = int(round(amount))
        elif nutrient_id == 1003:
            protein = int(round(amount))
        elif nutrient_id == 1004:
            fat = int(round(amount))
        elif nutrient_id == 1005:
            carbs = int(round(amount))

    return {
        "kcal": kcal,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }


class NutrientInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutrient
        fields = ["id", "name", "unit"]


class ProductNutrientSerializer(serializers.ModelSerializer):
    nutrient = NutrientInlineSerializer()

    class Meta:
        model = ProductNutrient
        fields = ["nutrient", "amount_per_100g"]


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

    def get_macros(self, obj):
        return get_product_macros_data(obj)

class ProductListQuerySerializer(serializers.Serializer):
    TAG_CHOICES = [
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

    PROP_CHOICES = [
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

    search = serializers.CharField(required=False, max_length=40)
    page = serializers.IntegerField(required=False, min_value=1)
    tag = serializers.ChoiceField(required=False, choices=TAG_CHOICES)
    prop = serializers.ListField(
        child=serializers.ChoiceField(choices=PROP_CHOICES),
        required=False,
    )

    def validate_search(self, value):
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.isalnum():
            raise serializers.ValidationError("Invalid search value.")
        return value



class ProductDetailSerializer(serializers.ModelSerializer):
    product_nutrients = ProductNutrientSerializer(many=True, read_only=True)
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
            "product_nutrients",
        ]

    def get_macros(self, obj):
        return get_product_macros_data(obj)


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
        allow_empty=True,
    )


class ProductSummaryResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    items = ProductSummaryItemSerializer(many=True)



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
        choices=["static", "mild", "moderate", "high", "exhausting"]
    )
    goal = serializers.ChoiceField(
        choices=["maintenance", "cut", "bulk"],
        default="maintenance",
        required=False,
    )


class MicroNormItemSerializer(serializers.Serializer):
    nutrient_id = serializers.IntegerField()
    nutrient_name = serializers.CharField()
    unit = serializers.CharField()
    recommended_amount = serializers.DecimalField(max_digits=10, decimal_places=4)
    upper_limit = serializers.DecimalField(max_digits=10, decimal_places=4, allow_null=True)
    source = serializers.CharField()
    note = serializers.CharField()


class MacroTargetsSerializer(serializers.Serializer):
    calories = serializers.DecimalField(max_digits=10, decimal_places=2)
    protein_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    fat_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    carbs_g = serializers.DecimalField(max_digits=10, decimal_places=2)


class NormsResponseSerializer(serializers.Serializer):
    bmi = serializers.DecimalField(max_digits=10, decimal_places=2)
    bmr = serializers.DecimalField(max_digits=10, decimal_places=2)
    tdee = serializers.DecimalField(max_digits=10, decimal_places=2)
    macro_targets = MacroTargetsSerializer()
    micro_targets = MicroNormItemSerializer(many=True)


class MealProductInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    grams = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.01)


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


class ProductTagsSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField())
    properties = serializers.ListField(child=serializers.CharField())


class ProductMacrosSerializer(serializers.Serializer):
    kcal = serializers.IntegerField()
    protein = serializers.IntegerField()
    fat = serializers.IntegerField()
    carbs = serializers.IntegerField()


from rest_framework import serializers


class ProductItemSerializer(serializers.Serializer):
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


class ProductMicroSerializer(serializers.Serializer):
    name = serializers.CharField()
    unit = serializers.CharField()
    amount = serializers.IntegerField()


class ProductBatchDetailResponseSerializer(serializers.Serializer):
    item = ProductItemSerializer(allow_null=True)
    micro = ProductMicroSerializer(many=True)