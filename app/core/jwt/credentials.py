"""FastAPI JWT backed credentials."""

from typing import TYPE_CHECKING

from starlette.authentication import AuthCredentials

if TYPE_CHECKING:
    from collections.abc import Sequence


class FrozenAuthCredentials(AuthCredentials):
    """Custom AuthCredentials class that uses a frozenset for scopes to ensure immutability."""

    def __init__(self, scopes: Sequence[str] | None = None) -> None:
        """Initialize the FrozenAuthCredentials with an optional sequence of scopes."""

        self.scopes = frozenset() if scopes is None else frozenset(scopes)
