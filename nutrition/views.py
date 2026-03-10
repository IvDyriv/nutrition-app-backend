from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, filters
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer, NormsResponseSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from nutrition.serializers import NormsInputSerializer
from nutrition.services.norms import (
    calc_bmi,
    calculate_bmr,
    calculate_tdee,
    calculate_macro_targets,
    get_micro_norms,
    q,
)



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
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        qs = Product.objects.all().order_by("id")

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
    queryset = Product.objects.filter(is_active=True).prefetch_related("product_nutrients__nutrient")
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