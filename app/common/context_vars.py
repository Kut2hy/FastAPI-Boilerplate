"""Module for managing context variables in the application."""

from contextvars import ContextVar

ServerTimingAPI: ContextVar[dict[str, float] | None] = ContextVar("app_timings", default=None)
"""
Context variable to store timing information for the current request.
The dictionary maps timing names to their durations in milliseconds.
A `None` value means no timings have been recorded for this request.
Always `.set()` a *new* dict instead of mutating the one from `.get()`,
so timings never leak across requests via a shared default object.
"""
