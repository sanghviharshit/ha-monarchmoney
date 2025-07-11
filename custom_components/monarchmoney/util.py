"""Utility methods."""

from datetime import UTC, datetime
from re import sub


def format_date(date_str: str) -> str:
    """Format a date string into a human-readable relative time.

    Example usage:
    date_str = "2023-03-24T18:50:08.483121+00:00"
    human_readable_date = format_date(date_str)
    print(human_readable_date)  # Output: "19 hours ago" (assuming the current time is March 25, 2023 at 13:50 UTC)
    """

    # Convert the input date string to a datetime object
    dt = datetime.fromisoformat(date_str)

    # Get the current datetime in UTC timezone
    now = datetime.now(UTC)

    # Calculate the time difference between the input date and the current datetime
    delta = now - dt

    # Calculate the time difference in seconds
    seconds = delta.total_seconds()

    # Calculate the time difference in minutes, hours, and days
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    # Return a human-readable string
    if days > 0:
        return f"{int(days)} day{'s' if days > 1 else ''} ago"
    if hours > 0:
        return f"{int(hours)} hour{'s' if hours > 1 else ''} ago"
    if minutes > 0:
        return f"{int(minutes)} minute{'s' if minutes > 1 else ''} ago"
    return "just now"


def snake_case(input_str: str) -> str:
    """Convert a string to snake_case format.

    Snake case is a convention of writing compound words or phrases in which the elements are separated by an underscore.
    """
    return "_".join(
        sub(
            "([A-Z][a-z]+)",
            r" \1",
            sub("([A-Z]+)", r" \1", input_str.replace("-", " ")),
        ).split()
    ).lower()
