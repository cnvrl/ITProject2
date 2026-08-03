"""Small in-memory cache for prepared cyclone tables.

This module does not parse or normalise datasets. It only avoids reading the
same prepared table repeatedly while the API server is running.
"""

from __future__ import annotations

from threading import RLock
from typing import Any


class CacheManager:
    """Thread-safe in-memory key-value cache."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        """Return a cached value, or ``None`` when no value is stored."""
        with self._lock:
            return self._values.get(key)

    def set(self, key: str, value: Any) -> None:
        """Store a value under ``key``."""
        with self._lock:
            self._values[key] = value

    def clear(self, key: str | None = None) -> None:
        """Clear one cached value, or all values when ``key`` is omitted."""
        with self._lock:
            if key is None:
                self._values.clear()
            else:
                self._values.pop(key, None)


cache_manager = CacheManager()