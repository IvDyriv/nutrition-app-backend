from django.contrib import admin
from .models import Product, Nutrient, ProductNutrient


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "brand")
    list_filter = ("category", "data_source", "is_active")
    list_display = ("id", "name", "brand", "category", "data_source", "is_active", "updated_at")


@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_filter = ("unit", "is_macro")
    list_display = ("id", "name", "unit", "is_macro", "display_order")


@admin.register(ProductNutrient)
class ProductNutrientAdmin(admin.ModelAdmin):
    search_fields = ("product__name", "nutrient__name")
    list_display = ("id", "product", "nutrient", "amount_per_100g", "data_source", "updated_at")