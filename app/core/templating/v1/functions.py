"""Common functions for HTMX templating."""


def get_hx_id(fragment_name: str) -> str:
    """Get the HTMX ID for a given fragment name.

    Args:
        fragment_name: The name of the fragment.

    Returns:
        The HTMX ID for the fragment.

    """
    return f"HX-{fragment_name}-fragment"


def get_hx_target(fragment_name: str) -> str:
    """Get the HTMX target for a given fragment name.

    Args:
        fragment_name: The name of the fragment.

    Returns:
        The HTMX target for the fragment.

    """
    return f"#{get_hx_id(fragment_name)}"
