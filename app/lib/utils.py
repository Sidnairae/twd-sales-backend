"""
utils.py — small shared helpers used across multiple modules.

Keep this file focused: only add something here if it is genuinely reused
in two or more places.  One-off helpers belong in the module that uses them.
"""

from typing import Generator


def chunk(lst: list, size: int) -> Generator[list, None, None]:
    """
    Split a list into consecutive chunks of at most `size` items.

    Used when batch-inserting rows into Supabase to stay within
    the request payload limit (see IMPORT_CHUNK_SIZE in config.py).

    Example:
        list(chunk([1, 2, 3, 4, 5], 2))  →  [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
