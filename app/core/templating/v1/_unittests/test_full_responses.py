"""PyTest module for testing full HTMX responses."""

from pathlib import Path

import pytest
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app.core.templating.v1._unittests.make_test_request import make_request
from app.core.templating.v1.functions import get_hx_id, get_hx_target
from app.core.templating.v1.response import (
    EmptyResponseFragment,
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

# TODO: Following must be successfully rendered:
# - a full response with a single scope (main)
# - a full response with a single scope (non-main)
# - a full response with multiple scopes (main, menu, ...)
# - a full response with a single scope (main), but one of the wrappers are exchanged (e.g., menu is empty)

FULL_PAGE_SNIPPET = b"<!DOCTYPE html>"
BODY1_SNIPPET = b"<h1>Body 1</h1>"
SPLASH_BODY_SNIPPET = b"<h1>Splash Body</h1>"
MENU_SNIPPET = b'<li><a href="/item_1">Item 1</a></li>'
MAIN1_SNIPPET = b"<h1>Main 1</h1>"
MAIN2_SNIPPET = b"<h1>Main 2</h1>"
MAIN_W_PAGE_SNIPPET = b"<h1>Main with Pagination</h1>"
SIDEBAR1_SNIPPET = b"<h1>Sidebar 1</h1>"
SIDEBAR2_SNIPPET = b"<h1>Sidebar 2</h1>"
LIST_SNIPPET = b"<div>Item 1</div>\n<div>Item 2</div>\n<div>Item 3</div>"


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


def test_single_scope_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a simple opening of website that renders a plain main fragment in partial mode."""

    request = make_request()
    response = HTMXTemplatedResponse(
        request=request,
        fragments=(PartialResponseFragment(name="main", path="main_1.jinja.html"),),
    )

    assert response.status_code == 200
    assert FULL_PAGE_SNIPPET in response.body
    assert BODY1_SNIPPET in response.body
    assert MAIN1_SNIPPET in response.body
    assert MENU_SNIPPET in response.body
    assert SIDEBAR1_SNIPPET in response.body


def test_single_scope_of_nondefault_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a simple opening of website that renders a plain main fragment in partial mode.

    'main' fragment is a non-default fragment AKA it is not home page.
    """

    request = make_request()
    response = HTMXTemplatedResponse(
        request=request,
        fragments=(PartialResponseFragment(name="main", path="main_2.jinja.html"),),
    )

    assert response.status_code == 200
    assert FULL_PAGE_SNIPPET in response.body
    assert BODY1_SNIPPET in response.body
    assert MAIN2_SNIPPET in response.body
    assert MENU_SNIPPET in response.body
    assert SIDEBAR1_SNIPPET in response.body


def test_multiple_scopes_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a simple opening of website that renders multiple fragments in partial mode.

    Example would be logging in and rendering a user-specific menu fragment
    or rendering a sidebar with user-specific content.
    """

    request = make_request()
    response = HTMXTemplatedResponse(
        request=request,
        fragments=(
            PartialResponseFragment(name="main", path="main_2.jinja.html"),
            PartialResponseFragment(name="sidebar", path="sidebar_2.jinja.html"),
        ),
    )

    assert response.status_code == 200
    assert FULL_PAGE_SNIPPET in response.body
    assert BODY1_SNIPPET in response.body
    assert MAIN2_SNIPPET in response.body
    assert MENU_SNIPPET in response.body
    assert SIDEBAR2_SNIPPET in response.body


def test_paged_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a tab/site opening that has a pagination in the main content.

    Example would be a page with a list of items that has pagination in the main content.
    This in partial mode would render only list, but main would stay as it is.
    In full page mode, all must be rendered.
    """

    request = make_request()
    response = HTMXTemplatedResponse(
        request=request,
        fragments=(
            FullResponseFragment(name="main", path="main_w_page.jinja.html"),
            PartialResponseFragment(name="list", path="list.jinja.html"),
        ),
    )

    assert response.status_code == 200
    assert FULL_PAGE_SNIPPET in response.body
    assert BODY1_SNIPPET in response.body
    assert MAIN_W_PAGE_SNIPPET in response.body
    assert MENU_SNIPPET in response.body
    assert SIDEBAR1_SNIPPET in response.body
    assert LIST_SNIPPET in response.body


def test_splash_page_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a simple opening of website that renders a splash page in partial mode.

    Example would be a login page or HTTP error page. In these cases, only body fragment is rendered,
    but the rest of the page is not.
    """

    request = make_request()
    response = HTMXTemplatedResponse(
        request=request,
        fragments=(
            PartialResponseFragment(name="body", path="splash_body.jinja.html"),
            # NOTE: As these are not referenced in the body, they would not be rendered even if they were set to
            # non-empty fragments. But we set them to empty just to be sure they are not rendered.
            EmptyResponseFragment(name="menu"),
            EmptyResponseFragment(name="sidebar"),
            EmptyResponseFragment(name="main"),
        ),
    )

    assert response.status_code == 200
    assert FULL_PAGE_SNIPPET in response.body
    assert SPLASH_BODY_SNIPPET in response.body
    assert MAIN1_SNIPPET not in response.body
    assert MENU_SNIPPET not in response.body
    assert SIDEBAR1_SNIPPET not in response.body
