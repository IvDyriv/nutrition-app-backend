from rest_framework import serializers
from .models import Product, Nutrient, ProductNutrient


def get_product_macros_data(product):
    kcal = 0
    protein = 0
    fat = 0
    carbs = 0

    for item in product.product_nutrients.all():
        nutrient_name = item.nutrient.name.lower()
        amount = item.amount_per_100g or 0

        if "energy" in nutrient_name or "calorie" in nutrient_name:
            kcal = int(round(amount))
        elif "protein" in nutrient_name:
            protein = int(round(amount))
        elif "total lipid" in nutrient_name or nutrient_name == "fat" or "fat" in nutrient_name:
            fat = int(round(amount))
        elif "carbohydrate" in nutrient_name or "carb" in nutrient_name:
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