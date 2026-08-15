"""Unit tests for JWTMiddleware."""


from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid7

import jwt as pyjwt
import pytest
from asyncpg import InterfaceError

from app.core.jwt import access_token as at_module
from app.core.jwt import middleware as mw_module
from app.core.jwt import refresh_token as rt_module
from app.core.jwt.exceptions import MissingJWTClaimsError

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import Receive, Scope, Send

_TEST_SECRET = "test_secret_key_with_plenty_of_entropy_0123456789abcdef"  # noqa: S105
_TEST_HOST = "test_host"
_TEST_ISSUER = "test_issuer"


# ======================================================================================================================
# Helpers
# ======================================================================================================================
def _http_scope(cookies: dict[str, str] | None = None) -> dict[str, Any]:
    """Build a minimal ASGI HTTP scope with the given cookies."""
    headers: list[tuple[bytes, bytes]] = [(b"host", _TEST_HOST.encode())]

    if cookies:
        header_value = "; ".join(f"{name}={value}" for name, value in cookies.items())
        headers.append((b"cookie", header_value.encode()))

    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": b"",
    }


async def _noop_receive() -> dict[str, Any]:  # pragma: no cover - never awaited in practice
    return {
        "type": "http.request",
        "body": b"",
        "more_body": False,
    }


def _make_access_token(user_id: UUID | None = None, **extra_claims: str) -> at_module.AccessToken:
    """Generate a deterministic access token for tests."""
    claims = {"alias": "tester", "roles": "role1,role2"}
    claims.update(extra_claims)

    return at_module.AccessToken.generate_token(subject=user_id or uuid7(), **claims)


# ======================================================================================================================
# Fixtures
# ======================================================================================================================
@pytest.fixture(autouse=True)
def _configure_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch token classes and cookie kwargs to deterministic test values."""
    # BaseToken module-level hostname used for the audience claim.
    monkeypatch.setattr("app.core.jwt._base_token._HOSTNAME", _TEST_HOST)

    for cls in (at_module.AccessToken, rt_module.RefreshToken):
        monkeypatch.setattr(cls, "algorithm", "HS256")
        monkeypatch.setattr(cls, "_secret_key", _TEST_SECRET)
        monkeypatch.setattr(cls, "_issuer", _TEST_ISSUER)
        monkeypatch.setattr(cls, "acceptable_leeway", 0)

    # Cookie helpers refuse 'secure' on non-https in tests; strip it.
    monkeypatch.setitem(at_module.ACCESS_TOKEN_COOKIE_KWARGS, "secure", False)
    monkeypatch.setitem(rt_module.REFRESH_TOKEN_COOKIE_KWARGS, "secure", False)


@pytest.fixture
def stub_app() -> Callable[[str], tuple[Callable, dict[str, Any]]]:
    """Return a factory for stub ASGI apps that record their invocation."""

    def factory(behavior: str = "ok") -> tuple[Callable, dict[str, Any]]:
        state: dict[str, Any] = {"calls": 0, "scope": None, "send_is_callable": False}

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            state["calls"] += 1
            state["scope"] = scope
            state["send_is_callable"] = callable(send)

            if behavior == "raise":
                raise RuntimeError("endpoint exploded")

            if scope["type"] != "http":
                return  # lifespan/websocket stubs have nothing to send

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": b'{"ok": true}'})

        return app, state

    return factory


async def _run(middleware: Callable, scope: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the middleware and collect all outgoing ASGI messages."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await middleware(scope, _noop_receive, send)
    return sent


def _response_cookies(messages: list[dict[str, Any]]) -> SimpleCookie:
    """Parse all set-cookie headers from the captured response messages."""
    cookies: SimpleCookie = SimpleCookie()

    for message in messages:
        if message["type"] != "http.response.start":
            continue

        for name, value in message.get("headers", []):
            if name.lower() == b"set-cookie":
                cookies.load(value.decode())

    return cookies


# ======================================================================================================================
# Tests — pass-through paths
# ======================================================================================================================


@pytest.mark.asyncio
async def test_non_http_scope_passes_through_untouched(stub_app: Callable) -> None:
    """Lifespan/websocket scopes must bypass all JWT logic."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    scope = {"type": "lifespan"}
    await middleware(scope, _noop_receive, None)  # type: ignore -> send unused for lifespan

    assert state["calls"] == 1
    assert "user" not in scope
    assert "auth" not in scope


@pytest.mark.asyncio
async def test_guest_without_cookies_passes_through_as_unauthenticated(stub_app: Callable) -> None:
    """A request with no cookies reaches the app with the unauthenticated preset."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    await _run(middleware, _http_scope())

    assert state["calls"] == 1
    assert not state["scope"]["user"].is_authenticated
    assert state["scope"]["auth"].scopes == frozenset()


# ======================================================================================================================
# Tests — valid access token
# ======================================================================================================================


@pytest.mark.asyncio
async def test_valid_access_token_authenticates_request(stub_app: Callable) -> None:
    """A valid access token populates scope user/auth and passes through unchanged."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    token = _make_access_token()
    messages = await _run(middleware, _http_scope({"access_token": str(token)}))

    assert state["calls"] == 1
    assert state["scope"]["user"].is_authenticated
    assert state["scope"]["user"].display_name == "tester"
    assert state["scope"]["auth"].scopes == frozenset({"role1", "role2"})

    # No cookies are touched on the happy path.
    assert not _response_cookies(messages)


@pytest.mark.asyncio
async def test_access_token_with_empty_roles_gets_empty_scopes(stub_app: Callable) -> None:
    """An empty roles claim yields an empty scope set, not an error."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    token = _make_access_token(roles="")
    await _run(middleware, _http_scope({"access_token": str(token)}))

    assert state["calls"] == 1
    assert state["scope"]["user"].is_authenticated
    assert state["scope"]["auth"].scopes == frozenset()


# ======================================================================================================================
# Tests — invalid / missing access token with refresh fallback
# ======================================================================================================================


@pytest.mark.asyncio
async def test_expired_access_token_regenerates_via_refresh(
    stub_app: Callable, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid access + valid refresh → new access token cookie and authenticated request."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    refresh = rt_module.RefreshToken.generate_token(subject=uuid7())
    new_access = _make_access_token()

    async def fake_regenerate(token: rt_module.RefreshToken) -> at_module.AccessToken | None:
        assert token.token_id == refresh.token_id
        return new_access

    monkeypatch.setattr(mw_module, "regenerate_access_token", fake_regenerate)

    messages = await _run(
        middleware,
        _http_scope({"access_token": "garbage.token.value", "refresh_token": str(refresh)}),
    )

    assert state["calls"] == 1
    assert state["scope"]["user"].is_authenticated
    assert state["scope"]["user"].display_name == "tester"

    cookies = _response_cookies(messages)
    assert "access_token" in cookies
    assert cookies["access_token"].value == str(new_access)
    # Refresh cookie must not be deleted when regeneration succeeded.
    assert "refresh_token" not in cookies


@pytest.mark.asyncio
async def test_revoked_refresh_token_deletes_cookies(stub_app: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid refresh that the DB rejects → request proceeds unauthenticated, cookies cleared."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    refresh = rt_module.RefreshToken.generate_token(subject=uuid7())

    async def fake_regenerate(token: rt_module.RefreshToken) -> at_module.AccessToken | None:
        return None  # revoked / expired / unknown

    monkeypatch.setattr(mw_module, "regenerate_access_token", fake_regenerate)

    messages = await _run(
        middleware,
        _http_scope({"access_token": "garbage.token.value", "refresh_token": str(refresh)}),
    )

    assert state["calls"] == 1
    assert not state["scope"]["user"].is_authenticated

    cookies = _response_cookies(messages)
    # Both cookies must be present with an empty value (deletion headers).
    assert cookies["access_token"].value == ""
    assert cookies["refresh_token"].value == ""


@pytest.mark.asyncio
async def test_invalid_refresh_token_deletes_cookies(stub_app: Callable) -> None:
    """A refresh token failing signature validation also lands on the delete-cookie path."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    messages = await _run(
        middleware,
        _http_scope({"access_token": "bad", "refresh_token": "also.bad"}),
    )

    assert state["calls"] == 1
    assert not state["scope"]["user"].is_authenticated
    cookies = _response_cookies(messages)
    assert cookies["access_token"].value == ""
    assert cookies["refresh_token"].value == ""


@pytest.mark.asyncio
async def test_only_access_cookie_present_but_invalid(stub_app: Callable) -> None:
    """Access cookie alone, invalid → unauthenticated path with cookie cleanup."""
    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    messages = await _run(middleware, _http_scope({"access_token": "nope"}))

    assert state["calls"] == 1
    assert not state["scope"]["user"].is_authenticated
    cookies = _response_cookies(messages)
    assert cookies["access_token"].value == ""
    assert cookies["refresh_token"].value == ""


# ======================================================================================================================
# Tests — error handling
# ======================================================================================================================


@pytest.mark.asyncio
async def test_database_error_returns_503_and_preserves_cookies(
    stub_app: Callable, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A DB outage must produce a 503 and must NOT delete the client's session cookies."""


    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    refresh = rt_module.RefreshToken.generate_token(subject=uuid7())

    async def fake_regenerate(token: rt_module.RefreshToken) -> at_module.AccessToken | None:
        raise InterfaceError("connection closed")

    monkeypatch.setattr(mw_module, "regenerate_access_token", fake_regenerate)

    messages = await _run(
        middleware,
        _http_scope({"access_token": "bad", "refresh_token": str(refresh)}),
    )

    # The downstream app must NOT be invoked.
    assert state["calls"] == 0

    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 503

    # No set-cookie deletion headers.
    assert not _response_cookies(messages)


@pytest.mark.asyncio
async def test_unexpected_middleware_error_propagates(stub_app: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected bugs inside the middleware must propagate (to ServerErrorMiddleware)."""
    app, _ = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    async def fake_regenerate(token: rt_module.RefreshToken) -> at_module.AccessToken | None:
        raise AssertionError("totally unexpected")

    monkeypatch.setattr(mw_module, "regenerate_access_token", fake_regenerate)

    refresh = rt_module.RefreshToken.generate_token(subject=uuid7())

    with pytest.raises(AssertionError, match="totally unexpected"):
        await _run(
            middleware,
            _http_scope({"access_token": "bad", "refresh_token": str(refresh)}),
        )


@pytest.mark.asyncio
async def test_endpoint_exception_propagates_untouched(stub_app: Callable) -> None:
    """Endpoint exceptions must bubble up — the middleware must not swallow them."""
    app, _ = stub_app(behavior="raise")
    middleware = mw_module.JWTMiddleware(app)

    token = _make_access_token()

    with pytest.raises(RuntimeError, match="endpoint exploded"):
        await _run(middleware, _http_scope({"access_token": str(token)}))


# ======================================================================================================================
# Tests — token edge cases
# ======================================================================================================================


@pytest.mark.asyncio
async def test_access_token_missing_alias_claim_raises(stub_app: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """A correctly-signed access token missing the required alias claim is a minting bug → 500."""


    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    user_id = uuid7()
    # Token signed correctly but deliberately missing the alias claim.
    bad_access = at_module.AccessToken.generate_token(subject=user_id, roles="role1")
    refresh = rt_module.RefreshToken.generate_token(subject=user_id)

    regenerate_called = False

    async def fake_regenerate(token: rt_module.RefreshToken) -> at_module.AccessToken | None:
        nonlocal regenerate_called
        regenerate_called = True
        return _make_access_token()

    monkeypatch.setattr(mw_module, "regenerate_access_token", fake_regenerate)

    # MissingJWTClaimsError must propagate out of the middleware (to ServerErrorMiddleware),
    # and the refresh fallback must NOT be reached.
    with pytest.raises(MissingJWTClaimsError):
        await _run(
            middleware,
            _http_scope({"access_token": str(bad_access), "refresh_token": str(refresh)}),
        )

    assert state["calls"] == 0
    assert not regenerate_called


@pytest.mark.asyncio
async def test_token_with_malformed_claims_raises(stub_app: Callable) -> None:
    """A token whose claims fail structural validation is a minting bug → propagates as error."""


    app, state = stub_app()
    middleware = mw_module.JWTMiddleware(app)

    # Signed with the right key but with a non-UUID subject → ValueError in from_string.
    forged = pyjwt.encode(
        {
            "jti": str(uuid7()),
            "iss": _TEST_ISSUER,
            "aud": _TEST_HOST,
            "sub": "not-a-uuid",
            "iat": 1,
            "nbf": 1,
            "exp": 9999999999,
        },
        _TEST_SECRET,
        algorithm="HS256",
    )

    # The ValueError from UUID parsing propagates (caught by `except Exception` then re-raised).
    with pytest.raises(ValueError):  # noqa: PT011
        await _run(middleware, _http_scope({"access_token": forged}))

    assert state["calls"] == 0
