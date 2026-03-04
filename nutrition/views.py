from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, filters
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer


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