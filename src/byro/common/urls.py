from django.urls import path

from .views import LogInfoView, LoginView, logout_view

app_name = "common"
urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("log/info", LogInfoView.as_view(), name="log.info"),
]
