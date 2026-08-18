"""Header encoding utilities for ASGI scope."""


def to_header_name_fmt(header_name: str) -> bytes:
    """Convert a header name to the format used in the ASGI scope.

    Args:
        header_name (str): The header name to convert.

    Returns:
        bytes: The header name in ASGI scope format (lowercase and encoded in latin-1).

    """
    return header_name.lower().encode("latin-1")


def to_header_value_fmt(header_value: str) -> bytes:
    """Convert a header value to the format used in the ASGI scope.

    Args:
        header_value (str): The header value to convert.

    Returns:
        bytes: The header value in ASGI scope format (encoded in latin-1).

    """
    return header_value.encode("latin-1")
