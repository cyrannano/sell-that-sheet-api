from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter

from .models import TranslationExample
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
    UserView,
    UploadAuctionSetToBaselinkerView,
    PrepareTagFieldPreview,
    PerformOcrView,
    ListGroupUsersView,
    CompleteFilesView, CompleteAuctionSetFilesView, DescriptionTemplateViewSet,
    GetUsersDescriptionTemplates, KeywordTranslationViewSet, GetUsersKeywordTranslation, KeywordTranslationSearchView,
    TranslateView,
    ImageRotateView,
    DistinctAuctionParameterView,
    DistinctParameterView, SaveTranslationsView, ListTranslationsView,
    TranslationExampleViewSet, TagViewSet, CategoryTagViewSet, CategoryParameterViewSet,
    TranslateBaselinkerProductsView,
    BaselinkerInventoriesView,
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
router.register(r"descriptiontemplate", DescriptionTemplateViewSet)
router.register(r"keywordtranslation", KeywordTranslationViewSet)
router.register(r'translationexample', TranslationExampleViewSet)
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'category-tags', CategoryTagViewSet, basename='categorytag')
router.register(r"category-parameters", CategoryParameterViewSet, basename="category-parameter")

# router.register(r'keyword-translation', KeywordTranslationViewSet, basename='keyword-translation')


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
    path("api/user/", UserView.as_view(), name="user data"),
    path("api/user/<int:user_id>", UserView.as_view(), name="user data"),
    path("api/browse/", DirectoryBrowseView.as_view(), name="directory-browse"),
    path('api/complete-files/<int:auction_id>', CompleteFilesView.as_view(), name='complete_files'),
    path('api/complete-auctionset-files/<int:auction_set_id>', CompleteAuctionSetFilesView.as_view(), name='complete_auctionset_files'),
    path(
        "api/browse/<path:path>", DirectoryBrowseView.as_view(), name="directory-browse"
    ),
    path("api/translations/", ListTranslationsView.as_view(), name="list_translations"),
    path("api/translations/save/", SaveTranslationsView.as_view(), name="save_translations"),
    path('keyword-translation/search/', KeywordTranslationSearchView.as_view(), name='keyword-translation-search'),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/logout/", LogoutView.as_view(), name="logout"),
    path('api/perform-ocr/', PerformOcrView.as_view(), name='perform_ocr'),
    path('api/group-users/<str:group_name>/', ListGroupUsersView.as_view(), name='group_users'),
    path('api/description-templates/user/<int:user_id>/', GetUsersDescriptionTemplates.as_view(), name='description_templates'),
    path('api/keyword-translation/user/<int:user_id>/', GetUsersKeywordTranslation.as_view(), name='keyword_translation'),
    path('api/image-rotate/', ImageRotateView.as_view(), name='image_rotate'),
    path('distinct-auction-parameters/', DistinctAuctionParameterView.as_view(), name='distinct_auction_parameters'),
    path('distinct-parameters/', DistinctParameterView.as_view(), name='distinct_parameters'),
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
    path('auctionsets/baselinker/upload/<int:auctionset_id>', UploadAuctionSetToBaselinkerView.as_view(), name='upload_auctionset_to_baselinker'),
    path('tag-preview/', PrepareTagFieldPreview.as_view(), name='tag_preview'),
    path('api/translate/', TranslateView.as_view(), name='translate'),
    path('api/translate-bl-products/', TranslateBaselinkerProductsView.as_view(), name='translate_bl_products'),
    path('baselinker/inventories/', BaselinkerInventoriesView.as_view(), name='baselinker_inventories'),

]
