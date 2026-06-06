"""
Storage layer for caching parsed dictionary entries.

This package provides services for persisting parsed data to disk
to prevent redundant web requests and improve performance.
"""

from jpfm.storage.storage_service import StorageService, CURRENT_SCHEMA_VERSION

__all__ = ["StorageService", "CURRENT_SCHEMA_VERSION"]
