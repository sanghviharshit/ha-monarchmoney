"""Utility methods."""

from datetime import UTC, datetime
from typing import Any

from monarchmoney import MonarchMoney


def format_date(date_str: str) -> str:
    """Format a date string into a human-readable relative time.

    Example usage:
    date_str = "2023-03-24T18:50:08.483121+00:00"
    human_readable_date = format_date(date_str)
    print(human_readable_date)  # Output: "19 hours ago" (assuming the current time is March 25, 2023 at 13:50 UTC)
    """

    dt = datetime.fromisoformat(date_str)
    now = datetime.now(UTC)
    delta = now - dt
    seconds = delta.total_seconds()
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if days > 0:
        return f"{int(days)} day{'s' if days > 1 else ''} ago"
    if hours > 0:
        return f"{int(hours)} hour{'s' if hours > 1 else ''} ago"
    if minutes > 0:
        return f"{int(minutes)} minute{'s' if minutes > 1 else ''} ago"
    return "just now"


async def monarch_login(
    api: MonarchMoney,
    email: str,
    password: str,
    mfa_secret: str | None = None,
) -> None:
    """Log in to Monarch Money API with optional MFA secret.

    Shared by config_flow.py and update_coordinator.py to avoid duplication.
    Always disables session saving and session reuse to avoid blocking I/O.
    """
    kwargs: dict[str, Any] = {"save_session": False, "use_saved_session": False}
    if mfa_secret and mfa_secret.strip():
        kwargs["mfa_secret_key"] = mfa_secret.strip()
    await api.login(email=email, password=password, **kwargs)
