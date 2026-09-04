from django.urls import path

from . import views

app_name = "mfa"
urlpatterns = [
    path("settings/mfa/", views.MFASettingsView.as_view(), name="settings"),
    path("settings/mfa/setup/", views.SetupView.as_view(), name="setup"),
    path(
        "settings/mfa/recovery-codes/",
        views.RegenerateRecoveryCodesView.as_view(),
        name="recovery-codes",
    ),
    path("settings/mfa/disable/", views.DisableView.as_view(), name="disable"),
    path("login/mfa/", views.ChallengeView.as_view(), name="challenge"),
    path(
        "login/mfa/recovery/",
        views.ChallengeView.as_view(use_recovery=True),
        name="challenge.recovery",
    ),
]
