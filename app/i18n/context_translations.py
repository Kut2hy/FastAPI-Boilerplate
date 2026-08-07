"""Module that provides a custom translations class using ContextVars to manage the current locale."""

from contextvars import ContextVar
from gettext import translation

from app.i18n.config import (
    DEFAULT_LANGUAGE,
    IMPLEMENTED_LANGUAGES,
    LOCALIZATION_DIR,
)

CURRENT_LOCALE: ContextVar[str] = ContextVar("current_locale", default=DEFAULT_LANGUAGE)
"""
Context variable to track the current locale for translations, defaulting to 'en' (English).
Need to be careful as value is set after the LanguageMiddleware is executed,
so root scope translations may not be accurate.
"""

LOCALE_MAPPING = {
    lang: translation(domain="messages", localedir=LOCALIZATION_DIR, languages=[lang], fallback=True)
    for lang in IMPLEMENTED_LANGUAGES
}
"""Mapping of language codes to their corresponding gettext translation objects."""


class ContextVarTranslations:
    """Custom translations class that retrieves the current locale from a ContextVar."""

    @staticmethod
    def gettext(message: str) -> str:
        """Get the translated message for the current locale."""
        return LOCALE_MAPPING.get(CURRENT_LOCALE.get(), LOCALE_MAPPING[DEFAULT_LANGUAGE]).gettext(message)

    @staticmethod
    def ngettext(singular: str, plural: str, n: int) -> str:
        """Get the translated singular or plural message for the current locale based on the count."""
        return LOCALE_MAPPING.get(CURRENT_LOCALE.get(), LOCALE_MAPPING[DEFAULT_LANGUAGE]).ngettext(singular, plural, n)


gettext = ContextVarTranslations.gettext
"""Context-aware translation function for internationalization of messages in the application."""

ngettext = ContextVarTranslations.ngettext
"""Context-aware plural translation function for internationalization of messages in the application."""
