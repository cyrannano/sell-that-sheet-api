from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from .views import (
    AuctionViewSet,
    PhotoSetViewSet,
    PhotoViewSet,
    AuctionSetViewSet,
    AuctionParameterViewSet,
    ParameterViewSet,
    DirectoryBrowseView,
    LoginView,
    LogoutView,
    AllegroLoginView,
    AllegroCallbackView,
    AllegroGetCategoryParametersView,
    AllegroMatchCategoryView,
    AllegroGetCategoryByIdView,
    GetModelStructure,
    download_auctionset_xlsx,
)
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# DRF router for REST API viewsets
router = DefaultRouter()
router.register(r"auctions", AuctionViewSet)
router.register(r"photosets", PhotoSetViewSet)
router.register(r"photos", PhotoViewSet)
router.register(r"auctionsets", AuctionSetViewSet)
router.register(r"auctionparameters", AuctionParameterViewSet)
router.register(r"parameters", ParameterViewSet)

# Schema view for Swagger and ReDoc documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Auction API",
        default_version="v1",
        description="API for SellThatSheet",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # REST API urls
    path("", include(router.urls)),
    # Swagger and ReDoc documentation urls
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("admin/", admin.site.urls),
    path("api/browse/", DirectoryBrowseView.as_view(), name="directory-browse"),
    path(
        "api/browse/<path:path>", DirectoryBrowseView.as_view(), name="directory-browse"
    ),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/logout/", LogoutView.as_view(), name="logout"),
    path("allegro/login/", AllegroLoginView.as_view(), name="allegro_login"),
    path("allegro/callback/", AllegroCallbackView.as_view(), name="allegro_callback"),
    path(
        "allegro/get-category-parameters/<str:categoryId>",
        AllegroGetCategoryParametersView.as_view(),
        name="allegro_get_category_parameters",
    ),
    path(
        "allegro/match-category/<str:name>",
        AllegroMatchCategoryView.as_view(),
        name="allegro_match_category",
    ),
    path(
        "allegro/get-category-by-id/<str:categoryId>",
        AllegroGetCategoryByIdView.as_view(),
        name="allegro_get_category_by_id",
    ),
    path(
        "model-structure/<str:app_label>/<str:model_name>",
        GetModelStructure.as_view(),
        name="get_model_structure",
    ),
    path('download/auctionset/<int:auctionset_id>/', download_auctionset_xlsx, name='download_auctionset_xlsx'),
]
