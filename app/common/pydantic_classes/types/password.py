"""Pydantic password type definition."""

from re import compile as re_compile
from typing import Annotated

from pydantic import AfterValidator, Field, Secret

from app.common.pydantic_classes.types.config import STANDARD_VARCHAR_LENGTH
from app.common.regexp import RAW_PASSWORD_REGEXP

_RAW_PASSWORD_REGEXP = re_compile(RAW_PASSWORD_REGEXP)
"""Pre-compiled regex pattern for raw password validation."""


def pattern_validator(value: str) -> str:
    """Check if the password matches the required pattern.

    Args:
        value (str): The input password string.

    Returns:
        str: The validated password string.

    Raises:
        ValueError: If the password does not match the required pattern.

    """
    if _RAW_PASSWORD_REGEXP.fullmatch(value) is None:
        raise ValueError("Password does not match the required pattern.")

    return value


RawPassword = Secret[
    Annotated[
        str,
        # Avoids need to switch from rust-regex for this pattern, as it is using lookahead assertions.
        AfterValidator(pattern_validator),
        Field(
            description="A password string.",
            min_length=10,
            max_length=STANDARD_VARCHAR_LENGTH,
        ),
    ]
]
"""Raw password type for Pydantic models. Must be at least 10 characters long and match the required pattern."""


HashedPassword = Secret[
    Annotated[
        str,
        Field(
            description="A hashed password string.",
            # Just a simple pattern to ensure it is argon2id, no need for full validation here ... internally generated.
            pattern=r"^\$argon2id.*$",
        ),
    ]
]
"""
Hashed Argon2id password type for Pydantic models.
Must be at least 97 characters long and can be any string (no pattern validation).
"""
