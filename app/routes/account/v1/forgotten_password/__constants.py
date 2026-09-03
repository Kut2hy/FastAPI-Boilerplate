"""Common constants and functions for the forgotten password routes."""

from pathlib import Path

ABS_FS_PATH_PARTS = Path(__file__).parent.parts
"""Absolute path parts of the current file's forgotten password directory."""

FORGOTTEN_PASSW_FS_PATH_PARTS = ABS_FS_PATH_PARTS[ABS_FS_PATH_PARTS.index("routes") + 1 :]
"""File system path parts for the forgotten password routes, relative to the 'routes' directory."""

FORGOTTEN_PASSW_FS_PATH = "/".join(FORGOTTEN_PASSW_FS_PATH_PARTS)
"""File system path for the forgotten password routes, relative to the 'routes' directory."""

FORGOTTEN_PASSW_URL = "/" + FORGOTTEN_PASSW_FS_PATH.replace("_", "-")
"""URL path for the forgotten password routes, derived from the file system path."""

FORGOTTEN_PASSW_PREFIX = "forgotten_passwd"
"""Prefix for the forgotten password keys in Redis."""

FORGOTTEN_PASSW_KEY_TTL = 600
"""Expiration time in seconds for the forgotten password key sent to the user's email."""

FORGOTTEN_PASSW_LOCKOUT_TTL = 3600
"""Expiration time in seconds for the lockout period after exceeding forgotten password attempts."""

FORGOTTEN_PASSW_COOKIE_NAME = "forgotten_passw_token"
"""Name of the cookie used to store the forgotten password token."""

FORGOTTEN_PASSW_COOKIE_KWARGS = {
    "key": FORGOTTEN_PASSW_COOKIE_NAME,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": FORGOTTEN_PASSW_URL,
}
"""Default keyword arguments for the forgotten password cookie."""
