from django.urls import path
from .views import ProductListView, ProductDetailView
from .views import NormsCalculateView


urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("norms/calculate/", NormsCalculateView.as_view(), name="norms-calculate"),
]