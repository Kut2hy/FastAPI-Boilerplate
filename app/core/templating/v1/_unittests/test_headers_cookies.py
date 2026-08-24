"""Unit tests for headers and cookies handling."""

from pathlib import Path

import pytest  # noqa: TC002
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app.core.templating.v1._unittests.make_test_request import make_request
from app.core.templating.v1.functions import get_hx_id, get_hx_target
from app.core.templating.v1.response import (
    FullResponseFragment,
    HTMXTemplatedResponse,
    PartialResponseFragment,
)

TEST_JINJA_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "src"),
    autoescape=True,
)
TEST_JINJA_ENV.globals["get_hx_id"] = get_hx_id
TEST_JINJA_ENV.globals["get_hx_target"] = get_hx_target
TEST_JINJA_TEMPLATES = Jinja2Templates(env=TEST_JINJA_ENV)

TEST_DEFAULT_FRAGMENT_TEMPLATES = {
    "head": FullResponseFragment(name="head", path="head.jinja.html"),
    "menu": FullResponseFragment(name="menu", path="menu.jinja.html"),
    "body": FullResponseFragment(name="body", path="body_1.jinja.html"),
    "sidebar": FullResponseFragment(name="sidebar", path="sidebar_1.jinja.html"),
}


@pytest.fixture(autouse=True)
def _configure_base_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatches the Jinja2Templates for testing purposes."""
    monkeypatch.setattr("app.core.templating.v1.response.JINJA_TEMPLATES", TEST_JINJA_TEMPLATES)
    monkeypatch.setattr("app.core.templating.v1.response.DEFAULT_FRAGMENT_TEMPLATES", TEST_DEFAULT_FRAGMENT_TEMPLATES)
    monkeypatch.setattr(
        "app.core.templating.v1.response.BASE_FULL_RESPONSE_TEMPLATE",
        TEST_JINJA_TEMPLATES.get_template("full.jinja.html"),
    )
    monkeypatch.setattr(
        "app.core.templating.v1.response.BASE_PARTIAL_RESPONSE_TEMPLATE",
        TEST_JINJA_TEMPLATES.get_template("partial.jinja.html"),
    )

def test_get_url_push(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the HX-Push-URL header is correctly set in the response."""

    # Make a full response with a specific URL to push
    full_response = HTMXTemplatedResponse(
        request=make_request(path="/new-url", method="GET"),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
    )

    assert full_response.status_code == 200
    assert full_response.headers.get("HX-Push-URL") == "/new-url"

    # Ensure mutability of headers
    full_response.headers["HX-Custom-Header"] = "CustomValue"

    assert full_response.headers.get("HX-Push-URL") == "/new-url"
    assert full_response.headers.get("HX-Custom-Header") == "CustomValue"

    # Make a partial response with a specific URL to push
    partial_response = HTMXTemplatedResponse(
        request=make_request(path="/partial-url", method="GET", headers={"HX-Request-type": "partial"}),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
    )

    assert partial_response.status_code == 200
    assert partial_response.headers.get("HX-Push-URL") == "/partial-url"

    # Ensure mutability of headers
    partial_response.headers["HX-Custom-Header"] = "CustomValue"

    assert partial_response.headers.get("HX-Push-URL") == "/partial-url"
    assert partial_response.headers.get("HX-Custom-Header") == "CustomValue"


def test_post_url_push(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the HX-Push-URL header is correctly set in the response for POST requests."""

    # Make a full response with a specific URL to push for a POST request
    full_response = HTMXTemplatedResponse(
        request=make_request(path="/post-url", method="POST"),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
    )

    assert full_response.status_code == 200
    assert full_response.headers.get("HX-Push-URL") is None  # For POST requests, HX-Push-URL should not be set

    # Ensure mutability of headers
    full_response.headers["HX-Custom-Header"] = "CustomValue"

    assert full_response.headers.get("HX-Push-URL") is None
    assert full_response.headers.get("HX-Custom-Header") == "CustomValue"

    partial_response = HTMXTemplatedResponse(
        request=make_request(path="/partial-post-url", method="POST", headers={"HX-Request-type": "partial"}),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
    )

    assert partial_response.status_code == 200
    assert partial_response.headers.get("HX-Push-URL") is None  # For POST requests, HX-Push-URL should not be set

    # Ensure mutability of headers
    partial_response.headers["HX-Custom-Header"] = "CustomValue"

    assert partial_response.headers.get("HX-Push-URL") is None
    assert partial_response.headers.get("HX-Custom-Header") == "CustomValue"


def test_endpoint_set_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that headers set in the endpoint are correctly included in the response."""

    response = HTMXTemplatedResponse(
        request=make_request(),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
        headers={"X-Test-Header": "TestValue"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Test-Header") == "TestValue"

    # Ensure mutability of headers
    response.headers["X-Test-Header"] = "NewValue"
    response.headers["X-Another-Header"] = "AnotherValue"

    assert response.headers.get("X-Test-Header") == "NewValue"
    assert response.headers.get("X-Another-Header") == "AnotherValue"


def test_cookie_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that cookies are correctly passed in the response."""

    response = HTMXTemplatedResponse(
        request=make_request(),
        fragments=(
            PartialResponseFragment(name="main", path="main_1.jinja.html"),
        ),
    )
    response.set_cookie(key="test_cookie", value="test_value")

    assert response.status_code == 200
    assert response.headers.get("set-cookie") is not None
    assert "test_cookie=test_value" in response.headers.get("set-cookie", "")
