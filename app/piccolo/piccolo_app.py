"""Import all of the Tables subclasses in your app here, and register them with the APP_CONFIG."""

from pathlib import Path

from piccolo.conf.apps import AppConfig, table_finder

CURRENT_DIRECTORY = Path(__file__).parent.resolve()
"""Get location of the current directory to build paths."""

PROJECT_ROOT = CURRENT_DIRECTORY.parent.parent.resolve()
"""Get location of the app root to build paths."""

MIGRATIONS_DIRECTORY = CURRENT_DIRECTORY / "migrations"
"""Get location of the migrations directory to build paths."""

TABLE_MODULES = [
    p.relative_to(PROJECT_ROOT).as_posix().rsplit(".", 1)[0].replace("/", ".")
    for p in (CURRENT_DIRECTORY / "tables").glob("*.py")
    if not p.name.startswith("_")
]
"""Get all of the table modules in the tables directory to register with the APP_CONFIG."""


APP_CONFIG = AppConfig(
    app_name="app",
    migrations_folder_path=MIGRATIONS_DIRECTORY,
    table_classes=table_finder(
        modules=TABLE_MODULES,
        exclude_imported=True,
    ),
    migration_dependencies=[],
    commands=[],
)
