from django.core.paginator import EmptyPage, Paginator
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import WholeWordSearchFilter
from .models import (
    MealLog,
    MealLogItem,
    Nutrient,
    NutrientNorm,
    Product,
    ProductNutrient,
    UserPreferences,
    UserProfile,
)
from .serializers import (
    AnalyzeMealInputSerializer,
    AnalyzeMealResponseSerializer,
    CompareWithNormsInputSerializer,
    CompareWithNormsResponseSerializer,
    NormsInputSerializer,
    NormsResponseSerializer,
    ProductBatchDetailResponseSerializer,
    ProductBatchRequestSerializer,
    ProductListQuerySerializer,
    ProductSummaryResponseSerializer,
    ProductTagsSerializer, UserProfileSerializer,
)
from .services.meal_analysis import analyze_meal
from .services.norm_comparison import compare_meal_with_norms
from .services.norms import calculate_norms_response
from .services.products import (
    build_product_detail,
    build_product_summary,
    filter_products_by_tag_and_properties,
    get_active_products_queryset,
    get_available_product_tags_and_properties,
    get_products_by_ids,
)


PRODUCTS_PAGE_SIZE = 10
MAX_BATCH_PRODUCTS = 40


@extend_schema(
    summary="List products",
    description="Returns paginated products summary list.",
    parameters=[
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Search by product name. Max 40 symbols.",
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number.",
        ),
        OpenApiParameter(
            name="tag",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Single main tag per product.",
        ),
        OpenApiParameter(
            name="prop",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            many=True,
            description="Multiple product properties.",
        ),
    ],
    responses={200: ProductSummaryResponseSerializer},
)
class ProductListView(generics.GenericAPIView):
    filter_backends = [WholeWordSearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        queryset = get_active_products_queryset().order_by("id")
        return filter_products_by_tag_and_properties(
            queryset,
            tag=self.request.query_params.get("tag"),
            properties=self.request.query_params.getlist("prop"),
        )

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)

        return queryset

    @extend_schema(operation_id="products_list")
    def get(self, request, *args, **kwargs):
        query_serializer = ProductListQuerySerializer(
            data=self._get_query_serializer_data(request)
        )

        if not query_serializer.is_valid():
            return Response(
                {"detail": "Invalid parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset())
        paginator = Paginator(queryset, PRODUCTS_PAGE_SIZE)
        page_number = query_serializer.validated_data.get("page", 1)

        try:
            page = paginator.page(page_number)
        except EmptyPage:
            return Response(
                {"detail": "Invalid parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "count": paginator.count,
                "items": [
                    build_product_summary(product)
                    for product in page.object_list
                ],
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_query_serializer_data(request) -> dict:
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

        properties = request.query_params.getlist("prop")
        if properties:
            query_data["prop"] = properties

        return query_data


@extend_schema(
    summary="Product detail",
    description="Returns full product in frontend-friendly format.",
    responses={200: ProductBatchDetailResponseSerializer},
)
class ProductDetailView(APIView):
    @extend_schema(operation_id="product_detail")
    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(
            Product.objects.prefetch_related("product_nutrients__nutrient"),
            pk=pk,
            is_active=True,
        )

        return Response(build_product_detail(product), status=status.HTTP_200_OK)


@extend_schema(
    summary="Calculate nutrition norms",
    description="Calculates BMI, BMR, TDEE, macro targets and micronutrient norms.",
    request=NormsInputSerializer,
    responses={200: NormsResponseSerializer},
)
class NormsCalculateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NormsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            calculate_norms_response(serializer.validated_data),
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Analyze meal",
    description="Calculates total nutrients and macros for a meal.",
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
    description="Analyzes a meal and compares consumed nutrients with user norms.",
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


@extend_schema(
    responses=ProductTagsSerializer,
    summary="Product tags and properties",
)
@api_view(["GET"])
def product_tags(request):
    return Response(
        get_available_product_tags_and_properties(),
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="products_batch",
    summary="Receive full products by ids",
    description="Accepts POST with JSON body {'ids': [1, 2, 3]}.",
    request=ProductBatchRequestSerializer,
    responses={200: ProductBatchDetailResponseSerializer(many=True)},
)
class ProductBatchView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ProductBatchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_ids = serializer.validated_data["ids"]

        if len(product_ids) > MAX_BATCH_PRODUCTS:
            return Response(
                {"detail": f"Too many items (max {MAX_BATCH_PRODUCTS})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        products_by_id = get_products_by_ids(product_ids)

        missing_ids = [
            product_id
            for product_id in product_ids
            if product_id not in products_by_id
        ]

        if missing_ids:
            return Response(
                {"detail": "One or more products not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            [
                build_product_detail(products_by_id[product_id])
                for product_id in product_ids
            ],
            status=status.HTTP_200_OK,
        )


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
            "Norms calculation",
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


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user profile",
        description="Returns the profile of the currently authenticated user.",
        responses={200: UserProfileSerializer},
    )
    def get(self, request, *args, **kwargs):
        profile = request.user.profile  # Запитуємо профіль через OneToOneField
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update user profile",
        description="Updates the profile of the currently authenticated user.",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def put(self, request, *args, **kwargs):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete user profile",
        description="Deletes the profile of the currently authenticated user.",
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        profile = request.user.profile
        profile.delete()
        return Response({"detail": "Profile deleted successfully."}, status=status.HTTP_204_NO_CONTENT)