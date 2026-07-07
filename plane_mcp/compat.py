"""Compatibility helpers for self-hosted Plane Community Edition.

Plane CE's public API (``/api/v1``) does not expose the newer ``*-lite``
endpoints used by some tools. When a lite endpoint responds with HTTP 404,
fall back to the equivalent full endpoint that CE supports.
"""

from collections.abc import Callable
from typing import TypeVar

from fastmcp.utilities.logging import get_logger
from plane.errors.errors import HttpError

logger = get_logger(__name__)

P = TypeVar("P")
F = TypeVar("F")


def with_ce_fallback(primary: Callable[[], P], fallback: Callable[[], F]) -> P | F:
    """Call primary; on HTTP 404 (endpoint missing on Plane CE) call fallback instead."""
    try:
        return primary()
    except HttpError as e:
        if e.status_code != 404:
            raise
        logger.info("Endpoint returned 404 (not available on this Plane edition), using CE-compatible fallback")
        return fallback()
