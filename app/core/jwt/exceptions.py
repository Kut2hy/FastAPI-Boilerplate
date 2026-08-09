"""Additional exceptions related to JWT handling."""


class MissingAccessTokenError(Exception):
    """Exception raised when an access token is missing from the request."""


class JWTTypeError(TypeError):
    """Exception raised when a JWT token has an invalid type or structure."""


class JWTValueError(ValueError):
    """Exception raised when a JWT token has invalid values or claims."""
