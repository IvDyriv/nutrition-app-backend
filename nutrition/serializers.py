from rest_framework import serializers
from .models import Product, Nutrient, ProductNutrient


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
    class Meta:
        model = Product
        fields = ["id", "name", "brand", "category", "tags", "properties"]



class ProductDetailSerializer(serializers.ModelSerializer):
    product_nutrients = ProductNutrientSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "category",
            "tags",
            "properties",
            "product_nutrients",
        ]


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