from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class SimpleTgAuthor:
    """Represents basic information about a post author."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None

@dataclass
class SimpleTgPost:
    """Represents basic information about a scraped Telegram post."""
    post_id: Optional[int] = None
    post_url: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[datetime] = None
    views: Optional[str] = None # e.g., '1.8K', kept as string for simplicity
    # Use field to provide a default_factory for mutable types like classes
    author: SimpleTgAuthor = field(default_factory=SimpleTgAuthor)
    # Add other fields as needed (e.g., media URLs)
    # image_urls: List[str] = field(default_factory=list)
    # video_urls: List[str] = field(default_factory=list)

@dataclass
class ScrapedPage:
    """Represents the results from scraping one page of a channel."""
    posts: List[SimpleTgPost] = field(default_factory=list)
    next_page_token: Optional[str] = None # e.g., the 'before' ID for the next request
    # channel_name: Optional[str] = None # Could add channel info here if needed