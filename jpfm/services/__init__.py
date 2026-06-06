"""
Services package for application-level business logic.

This package provides services that orchestrate between parsers, storage,
and the GUI layer. Services implement cache-aware patterns and coordinate
multi-step workflows.
"""

from jpfm.services.dictionary_manager import DictionaryManager

__all__ = ["DictionaryManager"]
