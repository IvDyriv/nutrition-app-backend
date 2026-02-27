from django.db import models


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