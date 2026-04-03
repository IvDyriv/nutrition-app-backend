from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from .filters import WholeWordSearchFilter
from .models import Product, Nutrient, ProductNutrient, NutrientNorm, UserProfile, UserPreferences, MealLog, MealLogItem
from .serializers import ProductListSerializer, ProductDetailSerializer, NormsResponseSerializer, ProductTagsSerializer, \
    ProductListQuerySerializer, ProductBatchDetailResponseSerializer
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


from django.core.paginator import Paginator, EmptyPage
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSummaryResponseSerializer
from .filters import WholeWordSearchFilter
from .serializers import get_product_macros_data


@extend_schema(
    summary="List products (summary)",
    description="Returns products summary list.",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="limit symbol amount 40 symbols MAX. Exclude special symbols",
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number",
        ),
        OpenApiParameter(
            name="tag",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=[
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
            ],
            description="Single main tag per product",
        ),
        OpenApiParameter(
            name="prop",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            many=True,
            enum=[
                "hi-prot",
                "hi-fat",
                "hi-carb",
                "hi-cal",
                "low-prot",
                "low-fat",
                "low-carb",
                "low-cal",
                "fiber",
            ],
            description="Multiple property tags per product",
        ),
    ],
    responses={200: ProductSummaryResponseSerializer},
)
class ProductListView(generics.GenericAPIView):
    filter_backends = [WholeWordSearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        qs = Product.objects.all().prefetch_related(
            "product_nutrients__nutrient"
        ).order_by("id")

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__contains=[tag])

        props = self.request.query_params.getlist("prop")
        if props:
            qs = qs.filter(properties__overlap=props)

        return qs

    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @extend_schema(operation_id="products_list",)
    def get(self, request, *args, **kwargs):
        query_data = {}

        search = request.query_params.get("search")
        if search not in (None, ""):
            query_data["search"] = search

        page = request.query_params.get("page")
        if page not in (None, ""):
            query_data["page"] = page

        tag = request.query_params.get("tag")
        if tag not in (None, ""):
            query_data["tag"] = tag

        props = request.query_params.getlist("prop")
        if props:
            query_data["prop"] = props

        query_serializer = ProductListQuerySerializer(data=query_data)

        if not query_serializer.is_valid():
            return Response({"detail": "Invalid parameters."}, status=400)

        qs = self.filter_queryset(self.get_queryset())

        paginator = Paginator(qs, 10)
        page_number = query_serializer.validated_data.get("page", 1)

        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            return Response({"detail": "Invalid parameters."}, status=400)

        items = []
        for product in page_obj.object_list:
            macros = get_product_macros_data(product)

            items.append({
                "id": product.id,
                "name": product.name,
                "cal": int(round(macros.get("kcal", 0))),
                "prot": int(round(macros.get("protein", 0))),
                "fat": int(round(macros.get("fat", 0))),
                "carb": int(round(macros.get("carbs", 0))),
                "tag": product.tags[0] if product.tags else None,
                "properties": product.properties or [],
            })

        return Response({
            "count": paginator.count,
            "items": items,
        })


def build_product_response(product):
    macros = get_product_macros_data(product)

    micro = []

    for pn in product.product_nutrients.all():
        nutrient = pn.nutrient

        if nutrient.usda_nutrient_id in [1008, 1003, 1004, 1005]:
            continue

        amount = pn.amount_per_100g or 0

        micro.append({
            "name": nutrient.name,
            "unit": nutrient.unit,
            "amount": int(round(float(amount))),
        })

    return {
        "item": {
            "id": product.id,
            "name": product.name,
            "cal": int(round(macros.get("kcal", 0))),
            "prot": int(round(macros.get("protein", 0))),
            "fat": int(round(macros.get("fat", 0))),
            "carb": int(round(macros.get("carbs", 0))),
            "tag": product.tags[0] if product.tags else None,
            "properties": product.properties or [],
        },
        "micro": micro,
    }


@extend_schema(
    summary="Product detail",
    description="Returns full product in frontend-friendly format.",
    responses={200: ProductBatchDetailResponseSerializer},
)
class ProductDetailView(APIView):
    @extend_schema(operation_id = "product_detail")
    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(
            Product.objects.prefetch_related("product_nutrients__nutrient"),
            pk=pk,
            is_active=True,
        )
        return Response(build_product_response(product))


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


@extend_schema(
    summary="Receive an array of Full products",
    request={
        "application/json": {
            "type": "array",
            "items": {"type": "integer"},
            "example": [1, 2, 3],
        }
    },
    responses={200: OpenApiTypes.OBJECT},
)


@extend_schema(
    summary="Receive an array of Full products",
    request=OpenApiTypes.OBJECT,
    responses={200: ProductBatchDetailResponseSerializer(many=True)},
)
class ProductBatchView(APIView):
    def post(self, request, *args, **kwargs):
        ids = request.data

        if not isinstance(ids, list):
            return Response(
                {"detail": "Invalid payload. Expected a list of product IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(ids) > 40:
            return Response(
                {"detail": "Too many items (max 40)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not all(isinstance(i, int) for i in ids):
            return Response(
                {"detail": "All product IDs must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        products = (
            Product.objects
            .filter(id__in=ids, is_active=True)
            .prefetch_related("product_nutrients__nutrient")
        )
        products_map = {product.id: product for product in products}

        result = []
        for product_id in ids:
            product = products_map.get(product_id)

            if not product:
                result.append({
                    "item": None,
                    "micro": [],
                })
                continue

            result.append(build_product_response(product))

        return Response(result, status=status.HTTP_200_OK)

