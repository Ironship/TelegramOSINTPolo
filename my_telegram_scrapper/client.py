import requests
from requests.exceptions import RequestException, ConnectionError, Timeout
from typing import Optional, Dict

from .parser import parse_page
from .models import ScrapedPage

class SimpleScraperClient:
    """
    A simple client to fetch and parse Telegram channel web preview pages.
    """
    BASE_URL: str = "https://t.me"
    DEFAULT_USER_AGENT: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    REQUEST_TIMEOUT: int = 15 # Slightly longer timeout

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """
        Initializes the requests session with default or provided headers.
        """
        self.session = requests.Session()
        # Set default headers to mimic a browser
        default_headers = {
            'User-Agent': self.DEFAULT_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        # Update with provided headers, overriding defaults if necessary
        self.session.headers.update(headers or default_headers)

    def get_channel_page(self, channel_username: str, before_token: Optional[str] = None) -> Optional[ScrapedPage]:
        """
        Fetches and parses a single page of posts from a channel's web view.

        Args:
            channel_username: The username of the target channel (without '@').
            before_token: The token/ID to fetch posts before this point (for pagination).

        Returns:
            A ScrapedPage object containing posts and next page token, or None on error.
        """
        url = f"{self.BASE_URL}/s/{channel_username}"
        params = {}
        if before_token:
            params['before'] = before_token

        try:
            response = self.session.get(url, params=params, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Check explicit status code, though raise_for_status covers most cases
            if response.status_code == 200:
                # Parse the HTML content
                return parse_page(response.text)
            else:
                # This case is less likely if raise_for_status() is used, but kept for safety
                print(f"Error: Received unexpected status code {response.status_code} for {url}")
                return None

        except Timeout:
             print(f"Error: Request timed out for {url}")
             return None
        except ConnectionError:
             print(f"Error: Could not connect to {url}. Check network connection.")
             return None
        except RequestException as e:
            # Catches other requests-related errors (like HTTPError from raise_for_status)
            print(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            # Catch potential errors during parsing (though should be handled in parser ideally)
            print(f"An unexpected error occurred processing channel '{channel_username}': {e}")
            return None

    def close(self):
        """Closes the underlying requests session."""
        if self.session:
            self.session.close()
            print("Requests session closed.") # Optional: confirmation

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures the session is closed when exiting a 'with' block."""
        self.close()