import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import get_user_model

_discovery_cache = {}


class OIDCError(Exception):
    pass


def is_oidc_configured():
    return bool(settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID)


def get_oidc_settings():
    return {
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID,
        "client_secret": settings.OIDC_CLIENT_SECRET,
        "admin_group": settings.OIDC_ADMIN_GROUP,
        "auto_create_account": settings.OIDC_AUTO_CREATE_ACCOUNT,
        "username_field": settings.OIDC_USERNAME_FIELD,
    }


def discover(issuer_url):
    if issuer_url in _discovery_cache:
        return _discovery_cache[issuer_url]
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url) as resp:
            doc = json.loads(resp.read().decode())
    except Exception as exc:
        raise OIDCError(f"Failed to fetch OIDC discovery document: {exc}") from exc
    _discovery_cache[issuer_url] = doc
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
        with urllib.request.urlopen(req) as resp:
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
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        raise OIDCError(f"Userinfo request failed: {exc}") from exc


def get_or_create_user(claims, access_token):
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

    admin_group = settings.OIDC_ADMIN_GROUP
    if admin_group:
        groups = claims.get("groups")
        if groups is None:
            if userinfo is None:
                userinfo = get_userinfo(access_token)
            groups = userinfo.get("groups", [])
        if admin_group not in groups:
            raise OIDCError(
                f"User is not a member of the required group '{admin_group}'"
            )

    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        pass

    if not settings.OIDC_AUTO_CREATE_ACCOUNT:
        raise OIDCError(
            f"No local account for '{username}' and auto-creation is disabled"
        )

    user = User.objects.create_user(username=username)
    user.set_unusable_password()
    user.save()
    return user
