from django.urls import path

from .views import LogInfoView, LoginView, OIDCCallbackView, OIDCLoginView, logout_view

app_name = "common"
urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("log/info", LogInfoView.as_view(), name="log.info"),
    path("oidc/login/", OIDCLoginView.as_view(), name="oidc-login"),
    path("oidc/callback/", OIDCCallbackView.as_view(), name="oidc-callback"),
]
