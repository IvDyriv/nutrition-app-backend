from django.contrib import admin
from .models import Product, Nutrient, ProductNutrient, NutrientNorm, UserProfile, UserPreferences, MealLog, MealLogItem


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


@admin.register(NutrientNorm)
class NutrientNormAdmin(admin.ModelAdmin):
    list_display = ("id", "nutrient", "sex", "age_min", "age_max", "recommended_amount", "upper_limit", "source", )
    list_filter = ("sex", "nutrient")
    search_fields = ("nutrient__name",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "sex", "age", "height_cm", "weight_kg", "body_fat_percent", "activity", "goal", )
    list_filter = ("sex", "activity", "goal")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_profile",
        "diet_type",
    )
    list_filter = ("diet_type",)
    search_fields = ("user_profile__id",)


class MealLogItemInline(admin.TabularInline):
    model = MealLogItem
    extra = 1


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_profile",
        "meal_type",
        "logged_at",
    )
    list_filter = ("meal_type", "logged_at")
    search_fields = ("user_profile__id",)
    inlines = [MealLogItemInline]


@admin.register(MealLogItem)
class MealLogItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "meal_log",
        "product",
        "grams",
    )
    search_fields = ("product__name",)