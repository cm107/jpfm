"""WordListItem dataclass for representing a word entry with metadata."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WordListItem:
    """Immutable word list item with rich metadata tracking.
    
    Attributes:
        word: The Japanese word (required).
        source: Origin of the word (e.g., "browser_history", "manual", "jisho").
        added_time: ISO format timestamp when word was added.
        hit_count: Number of times word appeared in history (0 for manual adds).
        first_hit_time: ISO format timestamp of first occurrence in history.
        last_hit_time: ISO format timestamp of last occurrence in history.
        origin_url: Source URL if applicable (None for manual adds).
        custom_metadata: Additional metadata stored as dict (parsing results, etc.).
    
    Raises:
        ValueError: If word is empty or timestamps are not ISO format.
    """
    
    word: str
    source: str
    added_time: str  # ISO format
    hit_count: int = 0
    first_hit_time: Optional[str] = None  # ISO format
    last_hit_time: Optional[str] = None  # ISO format
    origin_url: Optional[str] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate word and timestamp fields.
        
        Raises:
            ValueError: If word is empty or timestamps are invalid ISO format.
        """
        if not self.word or not self.word.strip():
            raise ValueError("word must not be empty")
        
        # Validate ISO format timestamps
        for ts_field in [self.added_time, self.first_hit_time, self.last_hit_time]:
            if ts_field is not None:
                try:
                    datetime.fromisoformat(ts_field)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid ISO format timestamp: {ts_field}")
    
    @classmethod
    def from_word(
        cls,
        word: str,
        source: str = "manual",
        added_time: Optional[str] = None,
        hit_count: int = 0,
        first_hit_time: Optional[str] = None,
        last_hit_time: Optional[str] = None,
        origin_url: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> "WordListItem":
        """Create a WordListItem with automatic timestamp defaults.
        
        Args:
            word: The Japanese word.
            source: Origin of the word (default: "manual").
            added_time: ISO format timestamp (default: now).
            hit_count: Number of history occurrences (default: 0).
            first_hit_time: First occurrence timestamp (default: None).
            last_hit_time: Last occurrence timestamp (default: None).
            origin_url: Source URL (default: None).
            custom_metadata: Additional metadata dict (default: empty dict).
        
        Returns:
            A new WordListItem instance.
        """
        if added_time is None:
            added_time = datetime.now().isoformat()
        
        return cls(
            word=word,
            source=source,
            added_time=added_time,
            hit_count=hit_count,
            first_hit_time=first_hit_time,
            last_hit_time=last_hit_time,
            origin_url=origin_url,
            custom_metadata=custom_metadata or {},
        )
