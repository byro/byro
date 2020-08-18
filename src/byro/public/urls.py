from django.conf.urls import include
from django.urls import re_path

from . import views

member_pages = [
    re_path(r"^$", views.MemberView.as_view(), name="member.dashboard"),
    re_path(r"^list$", views.MemberListView.as_view(), name="member.list"),
]

urlpatterns = [
    re_path(r"^member/(?P<secret_token>[^/]+)/", include((member_pages, "memberpage")))
]
app_name = "public"
