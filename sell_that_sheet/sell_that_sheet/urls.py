from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from .views import AuctionViewSet, \
    PhotoSetViewSet, \
    PhotoViewSet, \
    AuctionSetViewSet, \
    AuctionParameterViewSet, \
    ParameterViewSet, \
    DirectoryBrowseView, \
    LoginView, \
    LogoutView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# DRF router for REST API viewsets
router = DefaultRouter()
router.register(r'auctions', AuctionViewSet)
router.register(r'photosets', PhotoSetViewSet)
router.register(r'photos', PhotoViewSet)
router.register(r'auctionsets', AuctionSetViewSet)
router.register(r'auctionparameters', AuctionParameterViewSet)
router.register(r'parameters', ParameterViewSet)

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
    path('admin/', admin.site.urls),
    path('api/browse/', DirectoryBrowseView.as_view(), name='directory-browse'),
    path('api/browse/<str:path>', DirectoryBrowseView.as_view(), name='directory-browse'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),

]
