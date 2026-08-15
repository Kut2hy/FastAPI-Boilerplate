"""JWT middleware for FastAPI."""

from uuid import UUID

from starlette.authentication import BaseUser
from starlette.authentication import UnauthenticatedUser as _UnauthenticatedUser

# Convenience pass-through for the UnauthenticatedUser class from Starlette.
UnauthenticatedUser = _UnauthenticatedUser


class AuthenticatedUser(BaseUser):
    """Custom user class that extends Starlette's BaseUser."""

    def __init__(self, username: str, uuid: UUID) -> None:
        """Initialize the BaseUser with a username and a UUID.

        Args:
            username (str): The username of the user aka email address.
            uuid (UUID): The UUID of the user.

        Raises:
            TypeError: If the username is not a non-empty string or if the UUID is not a valid UUID instance.

        """

        if not isinstance(username, str) or username == "":
            raise TypeError("Username must be a non-empty string.")

        self.username = username

        if not isinstance(uuid, UUID):
            raise TypeError("UUID must be a valid UUID instance.")

        self.uuid = uuid

    @property
    def is_authenticated(self) -> bool:
        """Indicates whether the user is authenticated."""
        return True

    @property
    def display_name(self) -> str:
        """Returns the display name of the user, which is the email address."""
        return self.username

    @property
    def identity(self) -> str:
        """Returns the identity of the user, which is the UUID."""
        return str(self.uuid)
