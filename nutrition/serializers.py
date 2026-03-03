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
