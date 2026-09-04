from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.generic import FormView, TemplateView

from byro.mfa import services
from byro.mfa.forms import RecoveryCodeForm, TOTPTokenForm


class SafeNextMixin:
    """Validated ``next`` handling – no open redirects."""

    def get_default_next_url(self):
        return "/"

    def get_next_url(self):
        url = self.request.POST.get("next") or self.request.GET.get("next") or ""
        if url and url_has_allowed_host_and_scheme(
            url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return url
        return self.get_default_next_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.get_next_url()
        return context


def add_verification_error(form, result):
    if result.locked_until:
        form.add_error(
            None, _("Too many failed attempts. Please wait a moment and try again.")
        )
    else:
        form.add_error(None, _("The authentication code is invalid or has expired."))


class ChallengeView(SafeNextMixin, FormView):
    """Second login step: TOTP code or, alternatively, a recovery code."""

    template_name = "mfa/challenge.html"
    use_recovery = False

    def dispatch(self, request, *args, **kwargs):
        if services.get_confirmed_device(request.user) is None:
            if services.policy_requires_mfa():
                return redirect(
                    reverse("mfa:setup")
                    + "?"
                    + urlencode({"next": self.get_next_url()})
                )
            return redirect(self.get_next_url())
        if services.is_verified(request):
            return redirect(self.get_next_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return RecoveryCodeForm if self.use_recovery else TOTPTokenForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["use_recovery"] = self.use_recovery
        context["recovery_codes_available"] = (
            services.get_status(self.request.user).recovery_codes_remaining > 0
        )
        return context

    def form_valid(self, form):
        if self.use_recovery:
            result = services.verify_recovery_code(
                self.request, form.cleaned_data["code"]
            )
            if result.verified:
                messages.warning(
                    self.request,
                    ngettext(
                        "You signed in with a recovery code. %(count)d recovery code is left.",
                        "You signed in with a recovery code. %(count)d recovery codes are left.",
                        result.remaining_codes,
                    )
                    % {"count": result.remaining_codes},
                )
                return redirect(self.get_next_url())
        else:
            result = services.verify_totp(self.request, form.cleaned_data["token"])
            if result.verified:
                return redirect(self.get_next_url())
        add_verification_error(form, result)
        return self.form_invalid(form)


class MFASettingsView(TemplateView):
    template_name = "mfa/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = services.get_status(self.request.user)
        context["status"] = status
        context["can_disable"] = status.enabled and not status.required_by_policy
        return context


class SetupView(SafeNextMixin, FormView):
    """Enrollment: show QR code and manual key, confirm with a first code,
    then show the recovery codes once."""

    template_name = "mfa/setup.html"
    form_class = TOTPTokenForm

    def get_default_next_url(self):
        return reverse("mfa:settings")

    def dispatch(self, request, *args, **kwargs):
        if services.get_confirmed_device(request.user) is not None:
            messages.info(
                request,
                _("Multi-factor authentication is already enabled for your account."),
            )
            return redirect("mfa:settings")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.device = services.begin_enrollment(request.user)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.device = services.get_pending_device(request.user)
        if self.device is None:
            messages.error(request, _("The setup has expired. Please start again."))
            return redirect(
                reverse("mfa:setup") + "?" + urlencode({"next": self.get_next_url()})
            )
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config_url"] = self.device.config_url
        context["manual_key"] = self.device.manual_key
        return context

    def form_valid(self, form):
        result = services.confirm_enrollment(
            self.request, self.device, form.cleaned_data["token"]
        )
        if not result.verified:
            add_verification_error(form, result)
            return self.form_invalid(form)
        return render(
            self.request,
            "mfa/recovery_codes.html",
            {
                "headline": _("Multi-factor authentication is now enabled."),
                "codes": result.recovery_codes,
                "next": self.get_next_url(),
            },
        )


class RegenerateRecoveryCodesView(FormView):
    template_name = "mfa/confirm_action.html"
    form_class = TOTPTokenForm

    def dispatch(self, request, *args, **kwargs):
        if services.get_confirmed_device(request.user) is None:
            return redirect("mfa:settings")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_title"] = _("Generate new recovery codes")
        context["action_text"] = _(
            "All existing recovery codes stop working immediately. The new codes "
            "are shown once, store them in a safe place."
        )
        context["submit_label"] = _("Generate new recovery codes")
        context["submit_class"] = "btn-warning"
        return context

    def form_valid(self, form):
        result = services.regenerate_recovery_codes(
            self.request, form.cleaned_data["token"]
        )
        if not result.verified:
            add_verification_error(form, result)
            return self.form_invalid(form)
        return render(
            self.request,
            "mfa/recovery_codes.html",
            {
                "headline": _("New recovery codes"),
                "codes": result.recovery_codes,
                "next": reverse("mfa:settings"),
            },
        )


class DisableView(FormView):
    template_name = "mfa/confirm_action.html"
    form_class = TOTPTokenForm

    def dispatch(self, request, *args, **kwargs):
        if services.get_confirmed_device(request.user) is None:
            return redirect("mfa:settings")
        if services.policy_requires_mfa():
            messages.error(
                request,
                _(
                    "Multi-factor authentication is required for all administrators "
                    "and cannot be disabled."
                ),
            )
            return redirect("mfa:settings")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_title"] = _("Disable multi-factor authentication")
        context["action_text"] = _(
            "Your authenticator app and all recovery codes will be removed. "
            "Afterwards your account is only protected by your password."
        )
        context["submit_label"] = _("Disable MFA")
        context["submit_class"] = "btn-danger"
        return context

    def form_valid(self, form):
        result = services.disable_mfa_for_request(
            self.request, form.cleaned_data["token"]
        )
        if not result.verified:
            add_verification_error(form, result)
            return self.form_invalid(form)
        messages.success(
            self.request, _("Multi-factor authentication has been disabled.")
        )
        return redirect("mfa:settings")
