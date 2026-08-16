"""Pydantic validation code type definition."""

from typing import Annotated

from pydantic import Field, Secret

ValidationCode = Secret[
    Annotated[
        str,
        Field(
            description="A validation code string.",
            pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$",
            min_length=14,
            max_length=14,
        ),
    ]
]
"""Validation code type for Pydantic models. Must be exactly 14 characters long and match the required pattern."""
