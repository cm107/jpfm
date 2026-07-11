"""WordListModel service for managing word list state and operations."""
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from jpfm.models.word_list_item import WordListItem

logger = logging.getLogger(__name__)


class WordListModel(QObject):
    """Service to manage word list state with rich metadata.
    
    Wraps a list of WordListItem objects and provides methods for:
    - Adding/removing items
    - Looking up items by word
    - Updating metadata
    - Filtering (deferred to Phase 4)
    - Sorting (deferred to Phase 6)
    
    Emits signals on state changes for view updates.
    """
    
    items_changed = Signal()  # Emitted when items are added/removed/modified
    metadata_updated = Signal(str)  # Emitted with word when metadata changes
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize an empty word list model.
        
        Args:
            parent: Optional parent QObject for signal lifetime management.
        """
        super().__init__(parent)
        self._items: List[WordListItem] = []
        self._word_to_index: Dict[str, int] = {}  # Fast lookup by word
        logger.debug("WordListModel initialized")
    
    def add_items(self, items: List[WordListItem]) -> None:
        """Add multiple items to the model (or update if word already exists).
        
        If an item's word already exists, it is updated with the new metadata.
        
        Args:
            items: List of WordListItem to add.
        
        Raises:
            ValueError: If any item is invalid.
        """
        if not items:
            return
        
        for item in items:
            if not isinstance(item, WordListItem):
                raise ValueError(f"Expected WordListItem, got {type(item)}")
            
            if item.word in self._word_to_index:
                # Update existing item
                idx = self._word_to_index[item.word]
                self._items[idx] = item
                logger.debug(f"Updated word list item: {item.word}")
                self.metadata_updated.emit(item.word)
            else:
                # Add new item
                self._word_to_index[item.word] = len(self._items)
                self._items.append(item)
                logger.debug(f"Added word list item: {item.word}")
        
        self.items_changed.emit()
    
    def add_item(self, item: WordListItem) -> None:
        """Add a single item to the model.
        
        Args:
            item: WordListItem to add.
        """
        self.add_items([item])
    
    def remove_item(self, word: str) -> None:
        """Remove an item by word.
        
        Args:
            word: The word to remove.
        
        Raises:
            ValueError: If word does not exist in model.
        """
        if word not in self._word_to_index:
            raise ValueError(f"Word '{word}' not found in model")
        
        idx = self._word_to_index[word]
        removed = self._items.pop(idx)
        
        # Rebuild index (O(n) but necessary for correctness)
        self._word_to_index.clear()
        for i, item in enumerate(self._items):
            self._word_to_index[item.word] = i
        
        logger.debug(f"Removed word list item: {word}")
        self.items_changed.emit()
    
    def get_items(self) -> List[WordListItem]:
        """Get all items in the model (unfiltered).
        
        Returns:
            List of WordListItem.
        """
        return list(self._items)  # Return copy to prevent external mutation
    
    def get_by_word(self, word: str) -> Optional[WordListItem]:
        """Get a specific item by word.
        
        Args:
            word: The word to look up.
        
        Returns:
            WordListItem if found, None otherwise.
        """
        if word in self._word_to_index:
            idx = self._word_to_index[word]
            return self._items[idx]
        return None
    
    def update_metadata(
        self, word: str, metadata_key: str, value: Any
    ) -> None:
        """Update a metadata field for an item.
        
        Args:
            word: The word to update.
            metadata_key: The metadata key to update (e.g., "hit_count").
            value: The new value.
        
        Raises:
            ValueError: If word not found or key is invalid.
        """
        if word not in self._word_to_index:
            raise ValueError(f"Word '{word}' not found in model")
        
        idx = self._word_to_index[word]
        item = self._items[idx]
        
        # Validate key is a valid field
        if not hasattr(item, metadata_key):
            raise ValueError(
                f"WordListItem has no field '{metadata_key}'"
            )
        
        # Since WordListItem is frozen, we must recreate it
        item_dict = {
            "word": item.word,
            "source": item.source,
            "added_time": item.added_time,
            "hit_count": item.hit_count,
            "first_hit_time": item.first_hit_time,
            "last_hit_time": item.last_hit_time,
            "origin_url": item.origin_url,
            "custom_metadata": dict(item.custom_metadata),
        }
        item_dict[metadata_key] = value
        
        try:
            new_item = WordListItem(**item_dict)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to update metadata: {e}")
        
        self._items[idx] = new_item
        logger.debug(f"Updated metadata for '{word}': {metadata_key}={value}")
        self.metadata_updated.emit(word)
    
    def sort_by(self, criteria: str, reverse: bool = False) -> None:
        """Sort items in-place by a given criteria.
        
        Args:
            criteria: Sort criteria (word, source, hit_count, added_time, last_hit_time).
            reverse: If True, sort in descending order.
        
        Raises:
            ValueError: If criteria is invalid.
        """
        valid_criteria = {
            "word",
            "source",
            "hit_count",
            "added_time",
            "last_hit_time",
        }
        if criteria not in valid_criteria:
            raise ValueError(f"Invalid sort criteria: {criteria}")
        
        # Special handling for criteria with None values
        if criteria == "last_hit_time":
            # Sort with None values at the end
            self._items.sort(
                key=lambda x: (x.last_hit_time is None, x.last_hit_time),
                reverse=reverse,
            )
        else:
            self._items.sort(
                key=lambda x: getattr(x, criteria), reverse=reverse
            )
        
        # Rebuild index
        self._word_to_index.clear()
        for i, item in enumerate(self._items):
            self._word_to_index[item.word] = i
        
        logger.debug(f"Sorted word list by {criteria} (reverse={reverse})")
        self.items_changed.emit()
    
    def clear(self) -> None:
        """Clear all items from the model."""
        self._items.clear()
        self._word_to_index.clear()
        logger.debug("Cleared word list model")
        self.items_changed.emit()
    
    def count(self) -> int:
        """Get the number of items in the model.
        
        Returns:
            Number of items.
        """
        return len(self._items)
