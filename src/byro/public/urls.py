from django.urls import include, path

from . import views

member_pages = [
    path("", views.MemberView.as_view(), name="member.dashboard"),
    path("list", views.MemberListView.as_view(), name="member.list"),
]

urlpatterns = [
    path("member/<str:secret_token>/", include((member_pages, "memberpage")))
]
app_name = "public"
