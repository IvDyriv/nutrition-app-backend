from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import render
from rest_framework import generics
from .filters import WholeWordSearchFilter
from .models import Product, Nutrient, ProductNutrient, NutrientNorm, UserProfile, UserPreferences, MealLog, MealLogItem
from .serializers import ProductListSerializer, ProductDetailSerializer, NormsResponseSerializer, ProductTagsSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from nutrition.serializers import (
    NormsInputSerializer,
    AnalyzeMealInputSerializer,
    AnalyzeMealResponseSerializer,
    CompareWithNormsInputSerializer,
    CompareWithNormsResponseSerializer,
)


from nutrition.services.norms import (
    calc_bmi,
    calculate_bmr,
    calculate_tdee,
    calculate_macro_targets,
    get_micro_norms,
    q,
)
from nutrition.services.meal_analysis import analyze_meal
from nutrition.services.norm_comparison import compare_meal_with_norms


@extend_schema(
    summary="Products catalog",
    description="Returns paginated list of products. Supports search by name.",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Search by product name"
        ),

        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number"
        ),

        OpenApiParameter(
            name="tag",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            many=True,
            description="Filter by tags (AND). Example: ?tag=low_cal&tag=carb"
        ),

        OpenApiParameter(
            name="tag_any",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by tags (OR). Example: ?tag_any=low_cal,carb"
        ),

        OpenApiParameter(
            name="property",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            many=True,
            description="Filter by properties (AND). Example: ?property=hi-fat&property=hi-cal"
        ),

        OpenApiParameter(
            name="property_any",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by properties (OR). Example: ?property_any=hi-fat,hi-cal"
        ),
    ],
    responses=ProductListSerializer(many=True),
)
class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    filter_backends = [WholeWordSearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        qs = Product.objects.all().prefetch_related(
            "product_nutrients__nutrient").order_by("id")

        tags = self.request.query_params.getlist("tag")
        if tags:
            qs = qs.filter(tags__contains=tags)

        tag_any = self.request.query_params.get("tag_any")
        if tag_any:
            tag_list = tag_any.split(",")
            qs = qs.filter(tags__overlap=tag_list)

        props = self.request.query_params.getlist("property")
        if props:
            qs = qs.filter(properties__contains=props)

        prop_any = self.request.query_params.get("property_any")
        if prop_any:
            prop_list = prop_any.split(",")
            qs = qs.filter(properties__overlap=prop_list)

        return qs

@extend_schema(
    summary="Product detail",
    description="Returns product with full nutrient composition per 100g.",
    responses=ProductDetailSerializer,
)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True).prefetch_related("product_nutrients__nutrient").order_by("id")
    serializer_class = ProductDetailSerializer


@extend_schema(
    summary="Calculate nutrition norms",
    description="Calculates BMI, BMR, TDEE, macro targets and micronutrient norms based on user input.",
    request=NormsInputSerializer,
    responses={200: NormsResponseSerializer},
)
class NormsCalculateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NormsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        age = data["age"]
        sex = data["sex"]
        height_cm = data["height_cm"]
        weight_kg = data["weight_kg"]
        body_fat_percent = data.get("body_fat_percent")
        activity = data["activity"]
        goal = data.get("goal", "maintenance")

        bmi = q(calc_bmi(weight_kg, height_cm))
        bmr = calculate_bmr(
            weight=weight_kg,
            height=height_cm,
            sex=sex,
            age=age,
            body_fat_percent=body_fat_percent,
        )
        tdee = calculate_tdee(
            weight=weight_kg,
            height=height_cm,
            sex=sex,
            age=age,
            activity=activity,
            body_fat_percent=body_fat_percent,
        )
        macro_targets = calculate_macro_targets(tdee, goal)

        micro_targets_qs = get_micro_norms(age=age, sex=sex)

        seen_nutrients = set()
        micro_targets = []
        for item in micro_targets_qs:

            if item.nutrient_id in seen_nutrients:
                continue
            seen_nutrients.add(item.nutrient_id)

            micro_targets.append({
                "nutrient_id": item.nutrient.id,
                "nutrient_name": item.nutrient.name,
                "unit": item.nutrient.unit,
                "recommended_amount": item.recommended_amount,
                "upper_limit": item.upper_limit,
                "source": item.source,
                "note": item.note,
            })

        return Response(
            {
                "bmi": bmi,
                "bmr": bmr,
                "tdee": tdee,
                "macro_targets": macro_targets,
                "micro_targets": micro_targets,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Analyze meal",
    description="Calculates total nutrients and macros for a meal based on selected products and grams.",
    request=AnalyzeMealInputSerializer,
    responses={200: AnalyzeMealResponseSerializer},
)
class AnalyzeMealView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AnalyzeMealInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = analyze_meal(serializer.validated_data["products"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    summary="Compare meal with norms",
    description="Analyzes a meal and compares consumed nutrients with user nutrient norms.",
    request=CompareWithNormsInputSerializer,
    responses={200: CompareWithNormsResponseSerializer},
)
class CompareMealWithNormsView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CompareWithNormsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            result = compare_meal_with_norms(
                profile_id=data["profile_id"],
                products_data=data["products"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


def project_status_view(request):
    context = {
        "products_count": Product.objects.count(),
        "nutrients_count": Nutrient.objects.count(),
        "product_nutrients_count": ProductNutrient.objects.count(),
        "nutrient_norms_count": NutrientNorm.objects.count(),
        "user_profiles_count": UserProfile.objects.count(),
        "user_preferences_count": UserPreferences.objects.count(),
        "meal_logs_count": MealLog.objects.count(),
        "meal_log_items_count": MealLogItem.objects.count(),
        "ready_features": [
            "USDA import",
            "Products list API",
            "Product detail API",
            "Search by name",
            "Filter by tags/properties",
            "Swagger / OpenAPI",
            "Norms calculation (BMI, BMR, TDEE, macros, micros)",
            "Analyze meal",
            "Compare meal with norms",
            "User preferences",
            "Meal history models",
        ],
        "main_links": [
            {"name": "Swagger Docs", "url": "/api/docs/"},
            {"name": "Products API", "url": "/api/v1/products/"},
            {"name": "Product #1", "url": "/api/v1/products/1/"},
            {"name": "Admin", "url": "/admin/"},
        ],
    }
    return render(request, "nutrition/project_status.html", context)


@extend_schema(
    responses={
        200: {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
                "properties": {"type": "array", "items": {"type": "string"}},
            },
        }
    }
)

@extend_schema(
    responses=ProductTagsSerializer,
    summary="Product tags and properties",
)
@api_view(["GET"])
def product_tags(request):
    tags = set()
    properties = set()

    for product in Product.objects.all():
        if product.tags:
            tags.update(product.tags)
        if product.properties:
            properties.update(product.properties)

    return Response({
        "tags": sorted(tags),
        "properties": sorted(properties),
    })


