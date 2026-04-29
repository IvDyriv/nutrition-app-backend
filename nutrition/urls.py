from django.urls import path

from .views import (
    AnalyzeMealView,
    CompareMealWithNormsView,
    NormsCalculateView,
    ProductBatchView,
    ProductDetailView,
    ProductListView,
    product_tags,
    project_status_view, UserProfileView,
)


urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("norms/calculate/", NormsCalculateView.as_view(), name="norms-calculate"),
    path("nutrition/analyze-meal/", AnalyzeMealView.as_view(), name="analyze-meal"),
    path(
        "nutrition/compare-with-norms/",
        CompareMealWithNormsView.as_view(),
        name="compare-with-norms",
    ),
    path("status/", project_status_view, name="project-status"),
    path("products/tags/", product_tags, name="product-tags"),
    path("products/batch/", ProductBatchView.as_view(), name="product-batch"),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]
