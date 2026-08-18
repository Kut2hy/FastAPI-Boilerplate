"""Module for common regular expressions used in the application."""

from app.common.pydantic_classes.types.country import CountryCodeEnum

# ======================================================================================================================
# Phone number regex pattern
# ======================================================================================================================
_PHONE_RE_PATTERN_1 = r"\+(41|48|420|421)\d{9}"
"""Matches Czech, Slovak, Swiss and Polish phone numbers."""

_PHONE_RE_PATTERN_2 = r"\+(49)\d{10,11}"
"""Matches German phone numbers."""

_PHONE_RE_PATTERN_3 = r"\+(43)\d{10,13}"
"""Matches Austrian phone numbers."""

_PHONE_RE_PATTERN_4 = r"\+(36)\d{8,9}"
"""Matches Hungarian phone numbers."""

PHONE_NUMBER_REGEXP = r"^({})$".format(
    "|".join(
        [
            _PHONE_RE_PATTERN_1,
            _PHONE_RE_PATTERN_2,
            _PHONE_RE_PATTERN_3,
            _PHONE_RE_PATTERN_4,
        ]
    )
)
"""Matches implemented phone numbers."""

# ======================================================================================================================
# Postal code regex pattern
# ======================================================================================================================
_POSTAL_RE_PATTERN_1 = r"\d{3}\s?\d{2}"
"""Matches Czech and Slovak postal codes (e.g. ``110 00`` or ``11000``)."""

_POSTAL_RE_PATTERN_2 = r"\d{4}"
"""Matches Swiss, Austrian and Hungarian postal codes (e.g. ``8001``)."""

_POSTAL_RE_PATTERN_3 = r"\d{2}-\d{3}"
"""Matches Polish postal codes (e.g. ``00-950``)."""

_POSTAL_RE_PATTERN_4 = r"\d{5}"
"""Matches German postal codes (e.g. ``10115``)."""

POSTAL_CODE_REGEXP = r"^({})$".format(
    "|".join(
        [
            _POSTAL_RE_PATTERN_1,
            _POSTAL_RE_PATTERN_2,
            _POSTAL_RE_PATTERN_3,
            _POSTAL_RE_PATTERN_4,
        ]
    )
)
"""Matches implemented postal codes."""

# ======================================================================================================================
# Country code regex pattern
# ======================================================================================================================
def _to_re_fragment(code: str) -> str:
    """Convert a country code to a regex fragment that matches both uppercase and lowercase letters."""
    if len(code) != 2:
        raise ValueError("Country code must be 2 characters long")

    return f"(({code[0].lower()}|{code[0].upper()})({code[1].lower()}|{code[1].upper()}))"

COUNTRY_CODE_REGEXP = r"^({})$".format(
    "|".join([_to_re_fragment(code.value) for code in CountryCodeEnum])
)
"""Matches implemented country codes."""

# ======================================================================================================================
# Email regex pattern
# ======================================================================================================================
# ruff: disable[E501] -> Given pass for line length, as this is a standard regex for email validation.
EMAIL_REGEXP = r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`~\{\}\|\-]+@[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
"""Matches valid email addresses according to https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address """
# ruff: enable[E501]

# ======================================================================================================================
# Password regex pattern
# ======================================================================================================================
# ruff: disable[S105] -> Given pass for security, as this is a regex to enforce password complexity.
RAW_PASSWORD_REGEXP = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$"
"""
Matches valid passwords with at least 10 characters, including at least one uppercase letter,
one lowercase letter, one digit, and one special character.
"""
# ruff: enable[S105]
