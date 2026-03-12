"""Tests for my_telegram_scrapper.client – HTTP fetching with mocked network."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock

from my_telegram_scrapper.client import SimpleScraperClient
from my_telegram_scrapper.models import ScrapedPage, SimpleTgPost


# ---------------------------------------------------------------------------
# Minimal Telegram-like HTML page used in mock responses
# ---------------------------------------------------------------------------

_SINGLE_POST_HTML = """
<html><body>
  <div class="tgme_widget_message_wrap">
    <div class="tgme_widget_message" data-post-url="https://t.me/testchannel/1">
      <div class="tgme_widget_message_owner_name">
        <a href="https://t.me/testchannel"><span>Test Channel</span></a>
      </div>
      <div class="tgme_widget_message_text">A test post</div>
      <div class="tgme_widget_message_date">
        <time datetime="2024-03-01T09:00:00+00:00"></time>
      </div>
      <span class="tgme_widget_message_views">100</span>
    </div>
  </div>
  <a class="tme_messages_more" href="/s/testchannel?before=0">Load more</a>
</body></html>
"""

_EMPTY_PAGE_HTML = "<html><body></body></html>"


def _mock_response(html: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    resp.raise_for_status = MagicMock()  # does nothing by default
    return resp


# ---------------------------------------------------------------------------
# SimpleScraperClient.get_channel_page
# ---------------------------------------------------------------------------

class TestSimpleScraperClient:

    def test_successful_fetch_returns_scraped_page(self):
        with patch("requests.Session.get", return_value=_mock_response(_SINGLE_POST_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert isinstance(page, ScrapedPage)

    def test_successful_fetch_has_one_post(self):
        with patch("requests.Session.get", return_value=_mock_response(_SINGLE_POST_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert len(page.posts) == 1

    def test_post_content_is_correct(self):
        with patch("requests.Session.get", return_value=_mock_response(_SINGLE_POST_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page.posts[0].content == "A test post"

    def test_post_url_is_correct(self):
        with patch("requests.Session.get", return_value=_mock_response(_SINGLE_POST_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page.posts[0].post_url == "https://t.me/testchannel/1"

    def test_pagination_token_is_extracted(self):
        with patch("requests.Session.get", return_value=_mock_response(_SINGLE_POST_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page.next_page_token == "0"

    def test_before_token_passed_as_query_param(self):
        with patch("requests.Session.get", return_value=_mock_response(_EMPTY_PAGE_HTML)) as mock_get:
            with SimpleScraperClient() as client:
                client.get_channel_page("testchannel", before_token="50")
        _args, kwargs = mock_get.call_args
        assert kwargs.get("params", {}).get("before") == "50"

    def test_empty_page_returns_empty_post_list(self):
        with patch("requests.Session.get", return_value=_mock_response(_EMPTY_PAGE_HTML)):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page.posts == []
        assert page.next_page_token is None

    def test_timeout_error_returns_none(self):
        from requests.exceptions import Timeout
        with patch("requests.Session.get", side_effect=Timeout()):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page is None

    def test_connection_error_returns_none(self):
        from requests.exceptions import ConnectionError as RequestsConnectionError
        with patch("requests.Session.get", side_effect=RequestsConnectionError()):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page is None

    def test_http_error_returns_none(self):
        from requests.exceptions import HTTPError
        mock_resp = _mock_response("", status_code=404)
        mock_resp.raise_for_status.side_effect = HTTPError("404 Not Found")
        with patch("requests.Session.get", return_value=mock_resp):
            with SimpleScraperClient() as client:
                page = client.get_channel_page("testchannel")
        assert page is None

    def test_correct_url_is_requested(self):
        with patch("requests.Session.get", return_value=_mock_response(_EMPTY_PAGE_HTML)) as mock_get:
            with SimpleScraperClient() as client:
                client.get_channel_page("mychannel")
        called_url = mock_get.call_args[0][0]
        assert called_url == "https://t.me/s/mychannel"

    def test_context_manager_closes_session(self):
        with patch("requests.Session.get", return_value=_mock_response(_EMPTY_PAGE_HTML)):
            with patch("requests.Session.close") as mock_close:
                with SimpleScraperClient() as client:
                    client.get_channel_page("testchannel")
        mock_close.assert_called_once()
