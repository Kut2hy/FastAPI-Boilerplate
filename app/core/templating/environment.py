"""Jinja2 environment for the application's endpoints."""

from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemBytecodeCache, FileSystemLoader
from jinja2.ext import i18n
from jinjax import Catalog, JinjaX

from app.app_config import APP_SETTINGS
from app.core.templating.v1.functions import get_hx_id, get_hx_target
from app.i18n.context_translations import ContextVarTranslations

# ==========================================================================================
# Create a template loader
# ==========================================================================================
FS_LOADER = FileSystemLoader(APP_SETTINGS.templates_root)
"""File system loader for Jinja2 templates."""

# ==========================================================================================
# Prepare caching for Jinja2 templates
# ==========================================================================================
CACHE_DIR = Path(__file__).parent / "__jinja2_cache__"
"""Directory for storing Jinja2 bytecode cache files."""

if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(
        mode=700,
        parents=True,
        exist_ok=True,
    )

if APP_SETTINGS.in_development:
    # Clear the cache directory in development mode
    for template_cache in CACHE_DIR.iterdir():
        if template_cache.is_file():
            template_cache.unlink()

BYTECODE_CACHE = FileSystemBytecodeCache(str(CACHE_DIR))
"""Jinja2 bytecode cache instance."""

# ==========================================================================================
# Create the Jinja2 environment
# ==========================================================================================
JINJA_ENV = Environment(
    loader=FS_LOADER,
    autoescape=True,
    bytecode_cache=BYTECODE_CACHE,
    cache_size=1000,
    enable_async=False,
    extensions=[i18n, JinjaX],
    auto_reload=APP_SETTINGS.in_development,
)
"""Jinja2 environment for rendering templates."""

JINJA_ENV.install_gettext_translations(  # type: ignore -> function added by i18n
    ContextVarTranslations,
    newstyle=True,
)
"""Register the custom translations class with the Jinja2 environment."""

JINJAX_CATALOG = Catalog(
    jinja_env=JINJA_ENV,
    file_ext=".jinja.html",
    auto_reload=APP_SETTINGS.in_development,
)
"""JinjaX Catalog for managing server-side components."""

JINJAX_CATALOG.add_folder(APP_SETTINGS.templates_root / "components")
"""Add 'components' folder to JinjaX Catalog."""

# ==========================================================================================
# Globals, filters, and tests can be added to the Jinja2 environment below this breakpoint.
# ==========================================================================================
JINJA_ENV.globals["get_hx_id"] = get_hx_id
"""Add 'get_hx_id' global function to Jinja2 Environment for generating fragment HTMX IDs."""

JINJA_ENV.globals["get_hx_target"] = get_hx_target
"""Add 'get_hx_target' global function to Jinja2 Environment for generating fragment HTMX targets."""

# ==========================================================================================
# Create a Jinja2Templates instance for FastAPI
# ==========================================================================================
JINJA_TEMPLATES = Jinja2Templates(env=JINJA_ENV)
"""Jinja2Templates instance for rendering HTML templates."""
