"""Uvicorn entry point: validates the environment and configures logging."""

import stat
from argparse import ArgumentParser
from os import chdir, environ
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
"""Get the absolute path of the project root directory to build paths."""

PRIVATE = (
    stat.S_IRWXU,  # 700
    stat.S_IRUSR | stat.S_IWUSR,  # 600
)
"""Set permissions for private directories and files. Directories get 700, files get 600."""

PUBLIC = (
    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,  # 755
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,  # 644
)
"""Set permissions for public directories and files. Directories get 755, files get 644."""


def __set_permissions(directory: Path, dir_mode: int, file_mode: int) -> None:
    """Recursively set permissions for a directory and its contents.
    
    Args:
        directory (Path): The directory for which to set permissions.
        dir_mode (int): The permission mode to set for directories.
        file_mode (int): The permission mode to set for files.
    
    """
    if not directory.exists():
        return

    # Set permissions for the directory itself
    directory.chmod(dir_mode)

    # Set permissions for all files and subdirectories
    for item in directory.rglob("*"):
        item.chmod(dir_mode if item.is_dir() else file_mode)


def lazy_configuration_loading() -> tuple:
    """Lazy-load the logging configuration."""
    from app.app_config import APP_SETTINGS
    from app.core.logging.configuration import LOG_CONFIG

    return APP_SETTINGS, LOG_CONFIG


if __name__ == "__main__":
    import uvicorn

    parser = ArgumentParser(description="Run FastAPI application.")

    parser.add_argument(
        "--development",
        action="store_true",
        dest="development",
        help="Run the application in development mode with auto-reload.",
    )

    args = parser.parse_args()

    # ==================================================================================================================
    # Configure environment variables and permissions
    # ==================================================================================================================
    chdir(PROJECT_ROOT)

    environ["APP_ENVIRONMENT"] = "development" if args.development else "production"
    """Set the APP_ENVIRONMENT variable based on the --development flag."""

    environ["PROJECT_ROOT"] = str(PROJECT_ROOT)
    """Set the PROJECT_ROOT variable to the absolute path of the project root."""

    __set_permissions(PROJECT_ROOT / "app", *PRIVATE)
    __set_permissions(PROJECT_ROOT / "logs", *PRIVATE)
    __set_permissions(PROJECT_ROOT / "static", *PUBLIC)

    for f in PROJECT_ROOT.glob("*"):
        if f.is_file():
            f.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600

    # ==================================================================================================================
    # Run the Uvicorn server
    # ==================================================================================================================
    APP_SETTINGS, LOG_CONFIG = lazy_configuration_loading()
    """Lazy-load the application settings and logging configuration."""

    uvicorn.run(
        "app.main:app",
        host=APP_SETTINGS.host,
        port=APP_SETTINGS.port,
        workers=APP_SETTINGS.num_workers,
        loop="uvloop",
        http="httptools",
        reload=APP_SETTINGS.in_development,
        reload_dirs=[str(PROJECT_ROOT / "app")],
        log_level=LOG_CONFIG.get("root", {}).get("level", "info"),
        log_config=LOG_CONFIG,
        limit_concurrency=1000,
        timeout_keep_alive=5,
    )
