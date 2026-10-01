import json
import time
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from byro.common.models import LogEntry

GROUP_SYNC_LOG_ACTION = "byro.common.user.oidc_permissions_synced"
GROUP_SYNC_LOG_SOURCE = "internal: oidc_group_sync"

_discovery_cache = {}  # issuer_url -> (doc, fetched_at)
_DISCOVERY_TTL = 4 * 60 * 60  # 4 hours
_HTTP_TIMEOUT = 10


class OIDCError(Exception):
    pass


def is_oidc_configured():
    return bool(settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID)


def discover(issuer_url):
    cached = _discovery_cache.get(issuer_url)
    if cached and time.monotonic() - cached[1] < _DISCOVERY_TTL:
        return cached[0]
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT) as resp:
            doc = json.loads(resp.read().decode())
    except Exception as exc:
        raise OIDCError(f"Failed to fetch OIDC discovery document: {exc}") from exc
    _discovery_cache[issuer_url] = (doc, time.monotonic())
    return doc


def build_auth_url(redirect_uri, state, nonce):
    doc = discover(settings.OIDC_ISSUER_URL)
    params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
        }
    )
    return doc["authorization_endpoint"] + "?" + params


def exchange_code(code, redirect_uri):
    doc = discover(settings.OIDC_ISSUER_URL)
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
        }
    ).encode()
    req = urllib.request.Request(
        doc["token_endpoint"],
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.request.HTTPError as exc:
        body = exc.read().decode()
        raise OIDCError(f"Token exchange failed ({exc.code}): {body}") from exc
    except Exception as exc:
        raise OIDCError(f"Token exchange failed: {exc}") from exc


def validate_id_token(id_token, nonce):
    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError as exc:
        raise OIDCError("PyJWT[crypto] is required for OIDC support") from exc

    doc = discover(settings.OIDC_ISSUER_URL)
    jwks_uri = doc.get("jwks_uri")
    if not jwks_uri:
        raise OIDCError("OIDC discovery document missing jwks_uri")
    try:
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=settings.OIDC_CLIENT_ID,
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise OIDCError("ID token has expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise OIDCError("ID token audience mismatch") from exc
    except jwt.PyJWTError as exc:
        raise OIDCError(f"ID token validation failed: {exc}") from exc
    except Exception as exc:
        raise OIDCError(f"ID token validation failed: {exc}") from exc

    if claims.get("iss", "").rstrip("/") != settings.OIDC_ISSUER_URL.rstrip("/"):
        raise OIDCError(
            f"ID token issuer mismatch: got '{claims.get('iss')}', "
            f"expected '{settings.OIDC_ISSUER_URL}'"
        )
    if claims.get("nonce") != nonce:
        raise OIDCError("ID token nonce mismatch")
    return claims


def get_userinfo(access_token):
    doc = discover(settings.OIDC_ISSUER_URL)
    userinfo_endpoint = doc.get("userinfo_endpoint")
    if not userinfo_endpoint:
        raise OIDCError("OIDC discovery document missing userinfo_endpoint")
    req = urllib.request.Request(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        raise OIDCError(f"Userinfo request failed: {exc}") from exc


def get_configuration_error():
    """Why OIDC logins must be refused although OIDC is configured, or None.

    ``admin_group`` is the deprecated name of ``staff_group``. If both are set
    to different values there is no way to tell which one is meant, so no
    OIDC login is accepted until the configuration is unambiguous. Password
    logins are not affected.
    """
    if settings.OIDC_GROUP_CONFLICT:
        return "admin_group and staff_group are both set, but to different values"
    return None


def _groups_from(data):
    """The groups named by a ``groups`` claim, or None if the claim is missing.

    An empty claim is a valid statement (member of no group) and therefore
    returned as an empty list, not as None. Anything but a string or a list
    of strings is rejected, so that a malformed claim can never be read as
    "member of no group" and take permissions away.
    """
    groups = data.get("groups")
    if groups is None:
        return None
    if isinstance(groups, str):
        return groups.split()
    if isinstance(groups, (list, tuple)) and all(
        isinstance(group, str) for group in groups
    ):
        return list(groups)
    raise OIDCError("OIDC claim 'groups' has an unexpected format")


def get_groups(claims, access_token, userinfo=None):
    """Return the groups of the user: from the ID token if it carries a
    ``groups`` claim, otherwise from the userinfo endpoint. Only if neither
    has the claim, the user counts as a member of no group."""
    groups = _groups_from(claims)
    if groups is None:
        if userinfo is None:
            userinfo = get_userinfo(access_token)
        groups = _groups_from(userinfo)
    return groups or []


SYNCED_FLAGS = ("is_staff", "is_superuser")


def sync_permissions(user, is_staff=None, is_superuser=None):
    """Set the flags that are mapped to an OIDC group; ``None`` means that
    the flag is not mapped and must not be touched. Returns whether anything
    changed.

    The account is read again under a row lock, so the comparison, the write
    and the audit log entry are based on what is stored right now and not on
    the possibly outdated ``user`` object. Only flags that are mapped and
    actually differ are written: a flag that is not mapped can therefore
    never be changed, not even back to an older value. A deactivated account
    is left alone.

    The log entry only holds the old and new flags, never claims or groups.
    ``user`` is updated to the stored state afterwards.
    """
    wanted = {
        field: value
        for field, value in (("is_staff", is_staff), ("is_superuser", is_superuser))
        if value is not None
    }
    if not wanted:
        return False
    User = type(user)
    with transaction.atomic():
        try:
            current = User.objects.select_for_update().get(pk=user.pk)
        except User.DoesNotExist as exc:
            raise OIDCError("The local account does not exist any more") from exc
        old = {field: getattr(current, field) for field in SYNCED_FLAGS}
        changed = [
            field
            for field, value in wanted.items()
            if current.is_active and old[field] != value
        ]
        if changed:
            for field in changed:
                setattr(current, field, wanted[field])
            current.save(update_fields=changed)
            LogEntry.objects.create(
                content_object=current,
                action_type=GROUP_SYNC_LOG_ACTION,
                data={
                    "source": GROUP_SYNC_LOG_SOURCE,
                    "changes": {
                        field: [old[field], getattr(current, field)]
                        for field in SYNCED_FLAGS
                    },
                },
            )
    for field in (*SYNCED_FLAGS, "is_active"):
        setattr(user, field, getattr(current, field))
    return bool(changed)


def get_or_create_user(claims, access_token):
    """Return the local account for a validated OIDC login.

    Groups are resolved first. A new account gets its permissions from them
    once; an existing account is only changed if ``sync_groups`` is enabled,
    and then before the group check below, so that a rejected login never
    leaves revoked permissions behind. Whether the returned account may
    actually use the backend is decided by the caller.
    """
    User = get_user_model()
    username_field = settings.OIDC_USERNAME_FIELD
    username = claims.get(username_field)

    userinfo = None
    if not username:
        userinfo = get_userinfo(access_token)
        username = userinfo.get(username_field)
    if not username:
        raise OIDCError(
            f"OIDC claim '{username_field}' not found in ID token or userinfo"
        )

    staff_group = settings.OIDC_STAFF_GROUP
    superuser_group = settings.OIDC_SUPERUSER_GROUP
    in_staff_group = in_superuser_group = False
    if staff_group or superuser_group:
        groups = get_groups(claims, access_token, userinfo)
        in_staff_group = bool(staff_group) and staff_group in groups
        in_superuser_group = bool(superuser_group) and superuser_group in groups
    # With a staff group, OIDC logins are limited to the members of the
    # configured groups. Without one, every user of the provider may sign in.
    in_allowed_group = not staff_group or in_staff_group or in_superuser_group
    group_error = OIDCError("User is not a member of a group that may sign in")

    user = User.objects.filter(username=username).first()
    if user is None:
        if not in_allowed_group:
            raise group_error
        if not settings.OIDC_AUTO_CREATE_ACCOUNT:
            raise OIDCError(
                f"No local account for '{username}' and auto-creation is disabled"
            )
        # A provisioned account gets its permissions once, when it is created:
        # from the configured groups, and regular backend access if no staff
        # group is configured. It never becomes staff just for being superuser.
        user = User.objects.create_user(
            username=username,
            is_staff=in_staff_group if staff_group else True,
            is_superuser=in_superuser_group,
        )
        user.set_unusable_password()
        user.save()
        return user

    # A deactivated account is never changed; the caller rejects the login.
    if settings.OIDC_SYNC_GROUPS and user.is_active:
        sync_permissions(
            user,
            is_staff=in_staff_group if staff_group else None,
            is_superuser=in_superuser_group if superuser_group else None,
        )
    if not in_allowed_group:
        raise group_error
    return user
