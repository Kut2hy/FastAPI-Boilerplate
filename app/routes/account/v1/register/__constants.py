"""Common constants and functions for the registration routes."""

from pathlib import Path

ABS_FS_PATH_PARTS = Path(__file__).parent.parts
"""Absolute path parts of the current file's registration directory."""

REGISTRATION_FS_PATH_PARTS = ABS_FS_PATH_PARTS[ABS_FS_PATH_PARTS.index("routes") + 1 :]
"""File system path parts for the registration routes, relative to the 'routes' directory."""

REGISTRATION_FS_PATH = "/".join(REGISTRATION_FS_PATH_PARTS)
"""File system path for the registration routes, relative to the 'routes' directory."""

REGISTRATION_URL = "/" + REGISTRATION_FS_PATH.replace("_", "-")
"""URL path for the registration routes, derived from the file system path."""

REGISTRATION_PREFIX = "registration"
"""Prefix for the registration keys in Redis."""

REGISTRATION_KEY_TTL = 600
"""Expiration time in seconds for the registration key sent to the user's email."""

REGISTRATION_LOCKOUT_TTL = 3600
"""Expiration time in seconds for the lockout period after exceeding registration attempts."""

REGISTRATION_COOKIE_NAME = "registration_token"
"""Name of the cookie used to store the registration token."""

REGISTRATION_COOKIE_KWARGS = {
    "key": REGISTRATION_COOKIE_NAME,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": REGISTRATION_URL,
}
"""Default keyword arguments for the registration cookie."""
