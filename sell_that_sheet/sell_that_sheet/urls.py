from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuctionViewSet
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# DRF router for REST API viewsets
router = DefaultRouter()
router.register(r'auctions', AuctionViewSet)

# Schema view for Swagger and ReDoc documentation
schema_view = get_schema_view(
   openapi.Info(
      title="Auction API",
      default_version='v1',
      description="API for SellThatSheet",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # REST API urls
    path('', include(router.urls)),

    # Swagger and ReDoc documentation urls
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
