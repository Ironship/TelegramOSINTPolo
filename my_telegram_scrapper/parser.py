from bs4 import BeautifulSoup, Tag
from datetime import datetime
import re
from typing import List, Optional

# Import the dataclass models
from .models import SimpleTgPost, SimpleTgAuthor, ScrapedPage

TELEGRAM_BASE_URL: str = "https://t.me"

def _parse_post_id_from_url(url: Optional[str]) -> Optional[int]:
    """Extracts the post ID (integer) from a Telegram post URL."""
    if not url:
        return None
    # Regex: find digits preceded by '/' and followed by '?' or end of string
    match = re.search(r'/(\d+)(?:\?|$)', url)
    return int(match.group(1)) if match else None

def _parse_username_from_url(url: Optional[str]) -> Optional[str]:
    """Extracts the username from a Telegram profile or channel URL."""
    if not url:
        return None
    # Regex: find text after the last '/' but before '?' or end of string
    # Handles /s/channel, /channel, etc.
    match = re.search(r'/([^/?]+)$', url)
    # Alternative if above is too greedy: r'/s?/([^/?]+)'
    return match.group(1) if match else None

def _safe_find_text(element: Optional[Tag], selector: str, strip: bool = True) -> Optional[str]:
    """Safely finds an element using a CSS selector and returns its stripped text."""
    if not element:
        return None
    found = element.select_one(selector) # Use CSS selector
    return found.get_text(strip=strip) if found else None

def _safe_get_attr(element: Optional[Tag], selector: str, attribute: str) -> Optional[str]:
    """Safely finds an element using a CSS selector and returns a specific attribute."""
    if not element:
        return None
    found = element.select_one(selector)
    return found.get(attribute) if found else None

def parse_single_post(post_element: Tag) -> Optional[SimpleTgPost]:
    """Parses a single post HTML element (div.tgme_widget_message_wrap) into a SimpleTgPost object."""
    if not isinstance(post_element, Tag):
        return None

    post = SimpleTgPost() # Initialize with defaults from dataclass

    # Main message container is crucial
    widget_message = post_element.select_one(".tgme_widget_message")
    if not widget_message:
        print("Warning: Could not find main message container ('.tgme_widget_message') in post element.")
        return None # Cannot proceed without this

    # --- Basic Post Info ---
    data_post_url = widget_message.get('data-post-url')
    data_post = widget_message.get('data-post') # e.g., channel/12345
    if data_post_url:
        post.post_url = data_post_url
    elif data_post:
        post.post_url = f"{TELEGRAM_BASE_URL}/{data_post}"
    post.post_id = _parse_post_id_from_url(post.post_url)

    # --- Author Info ---
    # Look for the primary author name structure first
    author_link_tag = widget_message.select_one(".tgme_widget_message_owner_name a")
    if author_link_tag:
        post.author.profile_url = author_link_tag.get('href')
        post.author.username = _parse_username_from_url(post.author.profile_url)
        # Get text directly from the link's span if available
        author_name_span = author_link_tag.select_one("span") # or "span.name" if specific
        post.author.display_name = author_name_span.get_text(strip=True) if author_name_span else author_link_tag.get_text(strip=True)
    else:
        # Fallback for potentially different structures (e.g., forwarded messages might differ)
        author_user_tag = widget_message.select_one(".tgme_widget_message_from_author") # Check for forwarded author
        if author_user_tag:
            post.author.display_name = author_user_tag.get_text(strip=True)
            # Profile URL/username might not be available for forwarded authors in preview

    # --- Content ---
    # Select the text element, handling potential variations
    text_element = widget_message.select_one(".tgme_widget_message_text")
    if text_element:
        # Use separator='\n' to preserve line breaks within the post text
        post.content = text_element.get_text(separator='\n', strip=True)
    else:
        # Sometimes content is directly in the message bubble without a specific text class
        # This is less reliable and might grab unwanted text like "Forwarded message"
        # fallback_text = widget_message.select_one(".tgme_widget_message_bubble > .tgme_widget_message_text") # Example
        post.content = None # Or try a broader fallback if needed

    # --- Timestamp ---
    time_tag = widget_message.select_one(".tgme_widget_message_date time")
    if time_tag and time_tag.get('datetime'):
        try:
            # Attempt to parse ISO format timestamp (e.g., 2023-10-27T10:30:00+00:00)
            post.timestamp = datetime.fromisoformat(time_tag['datetime'])
        except ValueError:
            print(f"Warning: Could not parse timestamp datetime: {time_tag.get('datetime')}")
            post.timestamp = None # Handle parsing errors gracefully

    # --- Views ---
    # Views might be inside the date container or separate
    post.views = _safe_find_text(widget_message, ".tgme_widget_message_views")

    # --- Placeholder: Add parsing for media (images, videos) if needed ---
    # Example (very basic background image style):
    # photo_wrap = widget_message.select_one(".tgme_widget_message_photo_wrap[style*='background-image']")
    # if photo_wrap:
    #     style = photo_wrap.get('style', '')
    #     match = re.search(r"background-image:url\('(.*?)'\)", style)
    #     if match:
    #         # post.image_urls.append(match.group(1)) # Assuming image_urls list exists
    #         pass

    return post

def parse_page(html_content: str) -> ScrapedPage:
    """Parses the HTML content of a Telegram channel's web preview page."""
    soup = BeautifulSoup(html_content, 'lxml') # Use lxml parser
    page_result = ScrapedPage() # Initialize dataclass

    # Find all post container elements (usually divs with this class)
    post_elements = soup.select(".tgme_widget_message_wrap") # Use CSS selector

    if not post_elements:
         print("Warning: No post elements found with selector '.tgme_widget_message_wrap'. Page structure might have changed.")

    for element in post_elements:
        parsed_post = parse_single_post(element)
        if parsed_post:
            page_result.posts.append(parsed_post)

    # Find the token/ID for the *next* page (link to load *older* posts)
    # The 'Load more' link usually contains '?before=...'
    load_more_link = soup.select_one('a.tme_messages_more[href*="?before="]')
    if load_more_link:
        href = load_more_link.get('href', '')
        # Extract the 'before' parameter value
        match = re.search(r'[?&]before=(\d+)', href)
        if match:
            page_result.next_page_token = match.group(1)
        else:
            print("Warning: Found 'Load More' link but could not extract 'before' token.")

    # --- Placeholder: Add parsing for channel info (title, description, etc.) if needed ---
    # channel_info_header = soup.select_one(".tgme_channel_info_header_title")
    # if channel_info_header:
    #    page_result.channel_name = channel_info_header.get_text(strip=True)
    #    pass

    return page_result