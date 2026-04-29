from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views import MembershipViewSet, MemberViewSet

app_name = "api"

router = DefaultRouter()
router.register("members", MemberViewSet, basename="members")

membership_list = MembershipViewSet.as_view({"get": "list", "post": "create"})
membership_detail = MembershipViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = router.urls + [
    path(
        "members/<int:member_pk>/memberships/",
        membership_list,
        name="member-memberships-list",
    ),
    path(
        "members/<int:member_pk>/memberships/<int:pk>/",
        membership_detail,
        name="member-memberships-detail",
    ),
    path(
        "schema/",
        SpectacularAPIView.as_view(permission_classes=[], authentication_classes=[]),
        name="schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            url_name="api:schema", permission_classes=[], authentication_classes=[]
        ),
        name="swagger-ui",
    ),
]
