"""Base token implementation for JWT handling."""

from time import time
from typing import Any, Self
from uuid import UUID, uuid7

from jwt import decode, encode

from app.app_config import APP_SETTINGS
from app.core.jwt.exceptions import JWTTypeError, JWTValueError

_HOSTNAME = APP_SETTINGS.host
"""The hostname of the application."""

_STANDARD_CLAIMS: frozenset[str] = frozenset({"jti", "iss", "aud", "sub", "iat", "nbf", "exp"})
"""Standard JWT claims handled by BaseToken; used to filter extra claims efficiently."""


class BaseToken:
    """Base class for tokens.

    This class is not meant to be used directly. It should be subclassed by other token classes.
    When subclass instances are loaded from string, code to validate token and claims will be executed.
    If validation fails, an exception will be raised.

    Implemented claims:
    - 'jti' (JWT ID): A UUID that uniquely identifies the token.
    - 'iss' (Issuer): Identifies the principal that issued the JWT.
    - 'aud' (Audience): Identifies the recipients that the JWT is intended for.
    - 'sub' (Subject): A UUID that points to the user the token is issued for.
    - 'iat' (Issued At): The time at which the JWT was issued [seconds since epoch].
    - 'nbf' (Not Before): The time before which the JWT must not be accepted for processing [seconds since epoch].
    - 'exp' (Expiration Time): The time after which the JWT expires [seconds since epoch].
    """

    algorithm: str = ""
    """The algorithm used to sign the token. Subclasses must override this if they use a different algorithm."""

    allowed_extra_claims: frozenset[str] = frozenset()
    """
    A set of allowed extra claims that can be included in the token.
    Subclasses must override this to allow additional claims.
    """

    _issuer: str = ""
    """The issuer claim value for the token. Subclasses must override this if they use a different issuer."""

    _secret_key: str = ""
    """The secret key used to sign the token. Subclasses must override this if they use a different key."""

    time_to_live: int = 3600
    """The time to live for the token, in seconds. Subclasses must override this to set a different time to live."""

    acceptable_leeway: int = 0
    """The leeway for token expiration, in seconds. Subclasses can override this to set a different leeway."""

    __slots__ = (
        "audience",
        "expiration",
        "extra_claims",
        "issued_at",
        "issuer",
        "not_before",
        "subject",
        "token_id",
    )

    @classmethod
    def from_string(
        cls,
        token_str: str | bytes,
        leeway: int = 0,
    ) -> Self:
        """Parse a JWT string and returns an instance of the token class.

        Intention is that this method will be used to load tokens from string, and it will perform validation.
        This will be exclusively used as first validation done on cookie stored tokens in middleware,
        so that we can be sure that any token instance created from string is valid and can be used safely.

        Args:
            token_str (str | bytes): The JWT string to parse.
            leeway (int): The amount of leeway, in seconds, to allow when validating token expiration.

        Returns:
            BaseToken: An instance of the token class.

        Raises:
            JWTTypeError: If the token_str is not a string or bytes.
            JWTValueError: If the leeway is negative.
            InvalidTokenError: If the token is invalid or fails validation.

        """
        if not isinstance(token_str, (str, bytes)):
            raise JWTTypeError("Token must be a string or bytes.")

        if leeway < 0:
            raise JWTValueError("Leeway must be a non-negative integer.")

        claims: dict[str, Any] = decode(
            jwt=token_str,
            key=cls._secret_key,
            algorithms=[cls.algorithm],
            audience=str(_HOSTNAME),
            issuer=cls._issuer,
            leeway=leeway,
        )

        return cls(
            token_id=UUID(claims["jti"]),
            issuer=claims["iss"],
            audience=claims["aud"],
            subject=UUID(claims["sub"]),
            issued_at=int(claims["iat"]),
            not_before=int(claims["nbf"]),
            expiration=int(claims["exp"]),
            **{k: v for k, v in claims.items() if k not in _STANDARD_CLAIMS},
        )

    @classmethod
    def generate_token(
        cls,
        subject: UUID,
        **extra_claims: str,
    ) -> Self:
        """Generate a new token for the given user.

        Args:
            subject (UUID): The UUID of the subject to generate the token for.
            **extra_claims (dict[str, str]): Additional claims to include in the token.

        Returns:
            BaseToken: An instance of the token class.

        Raises:
            JWTTypeError: If the subject is not a UUID or if extra claims are not strings.
            JWTValueError: If extra claims contain keys that are not allowed.

        """
        if not isinstance(subject, UUID):
            raise JWTTypeError("Subject must be a UUID.")

        if extra_claims and not frozenset(extra_claims.keys()).issubset(cls.allowed_extra_claims):
            raise JWTValueError(f"Extra claims must be a subset of allowed extra claims: {cls.allowed_extra_claims}")

        # Common timestamps for token generation
        issued_at = int(time())

        return cls(
            token_id=uuid7(),
            issuer=cls._issuer,
            audience=str(_HOSTNAME),
            subject=subject,
            issued_at=issued_at,
            not_before=issued_at,
            expiration=issued_at + cls.time_to_live,
            **extra_claims,
        )

    def __init__(
        self,
        token_id: UUID,
        issuer: str,
        audience: str,
        subject: UUID,
        issued_at: int,
        not_before: int,
        expiration: int,
        **extra_claims: str,
    ) -> None:
        """Initialize the token instance with the provided claims.

        Args:
            token_id (UUID): The unique identifier for the token.
            issuer (str): The issuer of the token.
            audience (str): The audience for the token.
            subject (UUID): The subject of the token.
            issued_at (int): The time the token was issued, in seconds since epoch.
            not_before (int): The time before which the token is not valid, in seconds since epoch.
            expiration (int): The time the token expires, in seconds since epoch.
            **extra_claims (dict[str, str]): Additional claims to include in the token.

        Raises:
            JWTTypeError: If any of the claims are of the wrong type.
            JWTValueError: If any of the claims have invalid values.

        """
        if not isinstance(token_id, UUID):
            raise JWTTypeError("Token ID must be a UUID.")

        self.token_id: UUID = token_id

        if not isinstance(issuer, str):
            raise JWTTypeError("Issuer must be a string.")

        self.issuer: str = issuer

        if not isinstance(audience, str):
            raise JWTTypeError("Audience must be a string.")

        self.audience: str = audience

        if not isinstance(subject, UUID):
            raise JWTTypeError("Subject must be a UUID.")

        self.subject: UUID = subject

        if not isinstance(issued_at, int) or issued_at < 0:
            raise JWTTypeError("Issued At claim must be an integer representing seconds since epoch.")

        self.issued_at: int = issued_at

        if not isinstance(not_before, int) or not_before < 0:
            raise JWTTypeError("Not Before claim must be an integer representing seconds since epoch.")

        self.not_before: int = not_before

        if not isinstance(expiration, int) or expiration < 0:
            raise JWTTypeError("Expiration claim must be an integer representing seconds since epoch.")

        self.expiration: int = expiration

        if extra_claims and not frozenset(extra_claims.keys()).issubset(self.allowed_extra_claims):
            raise JWTValueError(f"Extra claims must be a subset of allowed extra claims: {self.allowed_extra_claims}")

        if extra_claims and not all(isinstance(value, str) for value in extra_claims.values()):
            raise JWTTypeError("Extra claim values must be strings.")

        self.extra_claims: dict[str, str] = extra_claims

    def __str__(self) -> str:
        """Serialize the token to a JWT string."""
        return encode(
            payload={
                "jti": str(self.token_id),
                "iss": self.issuer,
                "aud": self.audience,
                "sub": str(self.subject),
                "iat": self.issued_at,
                "nbf": self.not_before,
                "exp": self.expiration,
                **self.extra_claims,
            },
            key=self._secret_key,
            algorithm=self.algorithm,
        )

    def __eq__(
        self,
        value: object,
    ) -> bool:
        if not isinstance(value, BaseToken):
            return False

        return (
            self.token_id == value.token_id
            and self.issuer == value.issuer
            and self.audience == value.audience
            and self.subject == value.subject
            and self.issued_at == value.issued_at
            and self.not_before == value.not_before
            and self.expiration == value.expiration
            and self.extra_claims == value.extra_claims
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.token_id,
                self.issuer,
                self.audience,
                self.subject,
                self.issued_at,
                self.not_before,
                self.expiration,
                frozenset(self.extra_claims.items()),
            )
        )
