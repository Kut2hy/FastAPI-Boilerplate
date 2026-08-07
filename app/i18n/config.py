"""Configuration for internationalization (i18n)."""

from pathlib import Path

IMPLEMENTED_LANGUAGES = ("en", "cs", )
"""Tuple of language codes that are implemented and supported in the application."""

DEFAULT_LANGUAGE = "en"
"""Default language code to be used when no specific language is set or available."""

LOCALIZATION_DIR = Path(__file__).parent / "locales"
"""Directory where the gettext .mo files are stored for different languages."""
