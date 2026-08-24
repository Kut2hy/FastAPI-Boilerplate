"""Module for creating HTMX/HTTP templated responses."""

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

from fastapi import Request, status
from fastapi.responses import HTMLResponse

from app.core.templating.environment import JINJA_TEMPLATES
from app.i18n.context_translations import CURRENT_LOCALE, gettext

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from jinja2 import Template
    from starlette.background import BackgroundTask

    from app.core.jwt.users import AuthenticatedUser, UnauthenticatedUser


@dataclass(frozen=True, slots=True)
class ResponseFragment:
    """Data class representing a fragment of an HTMX response."""

    name: str
    """The name of the fragment, which corresponds to a scope in the base template."""

    path: str | None
    """Relative path from Jinja ENV template dir to fragment's template file."""

    hx_swap: str = "innerHTML"
    """The HTMX swap strategy to be applied when updating the DOM with this fragment."""


@dataclass(frozen=True, slots=True)
class FullResponseFragment(ResponseFragment):
    """Data class representing a fragment of a full HTMX response.

    Renders only if the request is a full page request (i.e., not a partial HTMX request).
    """


@dataclass(frozen=True, slots=True)
class PartialResponseFragment(ResponseFragment):
    """Data class representing a fragment of a partial HTMX response.

    Renders in both full page requests and partial HTMX requests.
    """


@dataclass(frozen=True, slots=True)
class EmptyResponseFragment(ResponseFragment):
    """Data class representing an empty fragment of an HTMX response.

    This can be used to suppress default fragments.
    """

    path: None = None


BASE_FULL_RESPONSE_TEMPLATE = JINJA_TEMPLATES.get_template("base/full.jinja.html")
"""Base/root template for full HTMX responses."""

BASE_PARTIAL_RESPONSE_TEMPLATE = JINJA_TEMPLATES.get_template("base/partial.jinja.html")
"""Base/root template for partial HTMX responses."""

DEFAULT_FRAGMENT_TEMPLATES = {
    "menu": FullResponseFragment(name="menu", path="layout/menu.jinja.html"),
    "body": FullResponseFragment(name="body", path="layout/body.jinja.html"),
}
"""Default page fragment templates for HTMX responses."""


class HTMXTemplatedResponse(HTMLResponse):
    """Custom HTML response class for rendering HTMX responses with Jinja templates.

    This class extends FastAPI's HTMLResponse to provide additional functionality for rendering
    HTMX responses with Jinja templates. It supports both full page and partial HTMX requests
    and allows for the inclusion of multiple response fragments.
    """

    media_type = "text/html"
    """Hard-coded media type for HTMX templated responses."""

    def __init__(
        self,
        request: Request,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        render_context: dict[str, Any] | None = None,
        title: str | None = None,
        push_url: str | None = None,
        fragments: tuple[FullResponseFragment | PartialResponseFragment | EmptyResponseFragment, ...] | None = None,
    ) -> None:
        """Initialize the HTMXTemplatedResponse.

        Args:
            request (Request):
                The FastAPI request object associated with this response.

            status_code (int, optional):
                The HTTP status code for the response. Defaults to 200 OK.

            headers (Mapping[str, str], optional):
                Additional headers to include in the response. Defaults to None.

            background (BackgroundTask, optional):
                A background task to run after the response is sent. Defaults to None.

            render_context (dict[str, Any], optional):
                Additional context to be passed to the Jinja template during rendering. Defaults to None.

            title (str, optional):
                The title to be used in the HTML head. Defaults to None, which will use "Untitled".

            push_url (str, optional):
                The URL to set for the HX-Push-URL header. Defaults to None.

            fragments (tuple[FullResponseFragment | PartialResponseFragment | EmptyResponseFragment, ...], optional):
                A tuple of response fragments to be included in the response. Defaults to None.

        """
        self._request = request
        """The FastAPI request object associated with this response."""

        self._raw_headers = {**headers} if headers is not None else {}
        """Uninitialized headers to be sent in the response.

        This is a mutable copy of the headers before they are processed by Starlette's response handling.
        """

        self.response_fragments = self.__build_fragment_schema(
            is_partial=self.is_partial_request,
            non_default_fragments=fragments or (),
        )
        """Fragments to be rendered in the response, with default fragments overridden by provided fragments."""

        self.render_context = render_context
        """Additional context to be passed to the Jinja template during rendering."""

        # HTMX restores history via a plain GET; pushing there re-adds the entry the user just left,
        #   which traps the back button.
        if request.headers.get("HX-History-Restore-Request") != "true" and (
            request.method.upper() == "GET" or push_url is not None
        ):
            # For GET requests, we want to set the HX-Push-URL header to the current URL by default.
            self._raw_headers["HX-Push-URL"] = push_url or str(request.url)

        self.title = title if title is not None else gettext("Untitled")
        """The title to be used in the HTML head."""

        rendered_content = self.rendered_content

        if self.is_partial_request:
            rendered_content = f"<head><title>{self.title}</title></head>\n" + rendered_content

        super().__init__(
            content=rendered_content,
            status_code=status_code,
            headers=self._raw_headers,
            background=background,
        )

    @cached_property
    def is_partial_request(self) -> bool:
        """Determine if the request is a partial HTMX request.

        Returns:
            True if the request is a partial HTMX request, False otherwise.

        """
        try:
            # It's important to check for the presence of the "hx-request-type='partial'" header.
            # Looking for "hx-request" alone is not sufficient,
            # as HTMX can have hx-target='body' and that is a full page request.
            return self._request.headers["hx-request-type"].lower() == "partial"

        except KeyError:
            # If the header is not present, we assume it's a full page request.
            # This would come from F5 refreshes, or users navigating directly to the URL.
            return False

    @property
    def base_render_template(self) -> Template:
        """Get the base/root template for rendering the response.

        Returns:
            The base template name.

        """
        return BASE_PARTIAL_RESPONSE_TEMPLATE if self.is_partial_request else BASE_FULL_RESPONSE_TEMPLATE

    @property
    def user(self) -> AuthenticatedUser | UnauthenticatedUser:
        """Get the authenticated user from the request state.

        Returns:
            FastAPI's user object, which can be an instance of AuthenticatedUser or UnauthenticatedUser.

        """
        return self._request.user

    @property
    def user_roles(self) -> frozenset[str]:
        """Get the authenticated user's roles from the request state.

        Returns:
            A frozenset of role names assigned to the authenticated user.

        """
        try:
            return self._request.auth.scopes

        except AttributeError:
            return frozenset()

    @property
    def response_nonce(self) -> str:
        """Get the nonce value from the request state."""
        return self._request.state.nonce

    @property
    def response_language(self) -> str:
        """Get the language code from the request state."""
        try:
            return self._request.state.language[:2] or "en"

        except AttributeError:
            return "en"

    @property
    def rendered_content(self) -> str:
        """Get the rendered HTML content for the response.

        Returns:
            The rendered HTML content as a string.

        """
        return self.base_render_template.render(
            fragments=self.response_fragments,
            nonce_hash=self.response_nonce,
            user=self.user,
            user_roles=self.user_roles,
            language=CURRENT_LOCALE.get() or "en",
            title=self.title,
            **(self.render_context or {}),
        )

    @staticmethod
    def __build_fragment_schema(
        is_partial: bool,
        non_default_fragments: Iterable[FullResponseFragment | PartialResponseFragment | EmptyResponseFragment],
    ) -> dict[str, FullResponseFragment | PartialResponseFragment]:
        """Build the schema of response fragments for the current request.

        Args:
            is_partial (bool):
                Whether the request is a partial HTMX request.

            non_default_fragments (Iterable[FullResponseFragment | PartialResponseFragment | EmptyResponseFragment]):
                Non-default fragments provided for the response.

        Returns:
            A dictionary mapping fragment names to their corresponding ResponseFragment instances.

        """
        filter_classes = (PartialResponseFragment,) if is_partial else (FullResponseFragment, PartialResponseFragment)
        fragment_schema = {
            **DEFAULT_FRAGMENT_TEMPLATES,
            **{f.name: f for f in non_default_fragments or []},
        }

        return {k: v for k, v in fragment_schema.items() if isinstance(v, filter_classes)}
