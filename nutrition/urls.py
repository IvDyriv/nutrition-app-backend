from django.urls import path
from .views import (ProductListView,
                    ProductDetailView,
                    AnalyzeMealView,
                    NormsCalculateView,
                    CompareMealWithNormsView,
                    project_status_view)


urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("norms/calculate/", NormsCalculateView.as_view(), name="norms-calculate"),
    path("nutrition/analyze-meal/", AnalyzeMealView.as_view(), name="analyze-meal"),
    path("nutrition/compare-with-norms/", CompareMealWithNormsView.as_view(), name="compare-with-norms"),
    path("status/", project_status_view, name="project-status"),
]