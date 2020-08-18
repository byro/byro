from django.urls import re_path

from .views import LogInfoView, LoginView, logout_view

app_name = "common"
urlpatterns = [
    re_path("^login/$", LoginView.as_view(), name="login"),
    re_path("^logout/$", logout_view, name="logout"),
    re_path("^log/info$", LogInfoView.as_view(), name="log.info"),
]
