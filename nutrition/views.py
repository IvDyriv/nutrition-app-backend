from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, filters
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer


@extend_schema(
    summary="Products catalog",
    description="Returns paginated list of products. Supports search by name.",
    parameters=[
        OpenApiParameter(name="search", required=False, type=str, description="Search by product name"),
        OpenApiParameter(name="page", required=False, type=int, description="Page number"),
    ],
    responses=ProductListSerializer(many=True),
)
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


@extend_schema(
    summary="Product detail",
    description="Returns product with full nutrient composition per 100g.",
    responses=ProductDetailSerializer,
)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True).prefetch_related("product_nutrients__nutrient")
    serializer_class = ProductDetailSerializer