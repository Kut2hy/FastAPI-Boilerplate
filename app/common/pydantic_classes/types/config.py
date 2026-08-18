"""Common configuration for types."""

NULLISH_STRINGS = frozenset(("", "null", "undefined"))
"""Strings that should be treated as None when validating nullish values."""

STANDARD_VARCHAR_LENGTH = 255
"""Maximum length for input strings to prevent excessively long inputs causing DoS attacks."""

INTEGER_MAX_VALUE = 2**31 - 1
"""PostgreSQL maximum value for integers based on the maximum input length."""
