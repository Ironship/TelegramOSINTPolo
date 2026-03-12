"""Tests for my_telegram_scrapper.parser – HTML → SimpleTgPost conversion."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from my_telegram_scrapper.parser import parse_page, parse_single_post
from my_telegram_scrapper.models import SimpleTgPost, ScrapedPage


# ---------------------------------------------------------------------------
# Helpers – build realistic Telegram web-preview HTML fragments
# ---------------------------------------------------------------------------

def _make_post_html(
    post_url: str = "https://t.me/testchannel/42",
    content: str = "Hello world",
    timestamp: str = "2024-01-15T10:30:00+00:00",
    views: str = "1.2K",
    author_href: str = "https://t.me/testchannel",
    author_name: str = "Test Channel",
) -> str:
    """Return a single .tgme_widget_message_wrap HTML fragment."""
    return f"""
    <div class="tgme_widget_message_wrap">
      <div class="tgme_widget_message"
           data-post-url="{post_url}">
        <div class="tgme_widget_message_owner_name">
          <a href="{author_href}"><span>{author_name}</span></a>
        </div>
        <div class="tgme_widget_message_text">{content}</div>
        <div class="tgme_widget_message_date">
          <time datetime="{timestamp}"></time>
        </div>
        <span class="tgme_widget_message_views">{views}</span>
      </div>
    </div>
    """


def _make_page_html(posts_html: str = "", before_token: str = "") -> str:
    """Wrap post fragments inside a full page-level shell."""
    pagination = ""
    if before_token:
        pagination = (
            f'<a class="tme_messages_more" href="/s/testchannel?before={before_token}">'
            "Load more</a>"
        )
    return f"<html><body>{posts_html}{pagination}</body></html>"


# ---------------------------------------------------------------------------
# parse_single_post
# ---------------------------------------------------------------------------

class TestParseSinglePost:
    def _parse(self, html: str) -> SimpleTgPost:
        soup = BeautifulSoup(html, "lxml")
        wrap = soup.select_one(".tgme_widget_message_wrap")
        assert wrap is not None, "Test HTML must contain .tgme_widget_message_wrap"
        return parse_single_post(wrap)

    def test_returns_simpletgpost(self):
        post = self._parse(_make_post_html())
        assert isinstance(post, SimpleTgPost)

    def test_post_url_extracted(self):
        post = self._parse(_make_post_html(post_url="https://t.me/testchannel/42"))
        assert post.post_url == "https://t.me/testchannel/42"

    def test_post_id_extracted(self):
        post = self._parse(_make_post_html(post_url="https://t.me/testchannel/99"))
        assert post.post_id == 99

    def test_content_extracted(self):
        post = self._parse(_make_post_html(content="Breaking news today"))
        assert post.content == "Breaking news today"

    def test_timestamp_extracted(self):
        post = self._parse(_make_post_html(timestamp="2024-06-01T08:00:00+00:00"))
        assert post.timestamp is not None
        assert post.timestamp.year == 2024
        assert post.timestamp.month == 6
        assert post.timestamp.day == 1

    def test_views_extracted(self):
        post = self._parse(_make_post_html(views="5.7K"))
        assert post.views == "5.7K"

    def test_author_display_name_extracted(self):
        post = self._parse(_make_post_html(author_name="OSINT Channel"))
        assert post.author.display_name == "OSINT Channel"

    def test_author_profile_url_extracted(self):
        post = self._parse(_make_post_html(author_href="https://t.me/osintbees"))
        assert post.author.profile_url == "https://t.me/osintbees"

    def test_author_username_extracted_from_url(self):
        post = self._parse(_make_post_html(author_href="https://t.me/osintbees"))
        assert post.author.username == "osintbees"

    def test_missing_message_container_returns_none(self):
        """A .tgme_widget_message_wrap without .tgme_widget_message returns None."""
        html = '<div class="tgme_widget_message_wrap"><p>No message here</p></div>'
        soup = BeautifulSoup(html, "lxml")
        wrap = soup.select_one(".tgme_widget_message_wrap")
        result = parse_single_post(wrap)
        assert result is None

    def test_non_tag_input_returns_none(self):
        result = parse_single_post("not a tag")  # type: ignore[arg-type]
        assert result is None

    def test_post_with_multiline_content(self):
        html = _make_post_html(content="Line one\nLine two\nLine three")
        post = self._parse(html)
        assert "Line one" in post.content
        assert "Line three" in post.content

    def test_post_without_content_gives_none(self):
        """A post with no .tgme_widget_message_text element results in content=None."""
        html = f"""
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message" data-post-url="https://t.me/ch/1">
            <div class="tgme_widget_message_date">
              <time datetime="2024-01-01T00:00:00+00:00"></time>
            </div>
          </div>
        </div>"""
        post = self._parse(html)
        assert post is not None
        assert post.content is None

    def test_invalid_timestamp_is_handled(self):
        """An un-parseable datetime attribute should result in timestamp=None."""
        html = f"""
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message" data-post-url="https://t.me/ch/2">
            <div class="tgme_widget_message_text">content</div>
            <div class="tgme_widget_message_date">
              <time datetime="not-a-date"></time>
            </div>
          </div>
        </div>"""
        post = self._parse(html)
        assert post is not None
        assert post.timestamp is None

    def test_post_url_falls_back_to_data_post_attribute(self):
        """If data-post-url is absent but data-post is present, URL is constructed."""
        html = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message" data-post="mychannel/7">
            <div class="tgme_widget_message_text">fallback url test</div>
            <div class="tgme_widget_message_date">
              <time datetime="2024-01-01T00:00:00+00:00"></time>
            </div>
          </div>
        </div>"""
        soup = BeautifulSoup(html, "lxml")
        wrap = soup.select_one(".tgme_widget_message_wrap")
        post = parse_single_post(wrap)
        assert post is not None
        assert "mychannel/7" in post.post_url


# ---------------------------------------------------------------------------
# parse_page
# ---------------------------------------------------------------------------

class TestParsePage:
    def test_returns_scraped_page(self):
        page = parse_page(_make_page_html())
        assert isinstance(page, ScrapedPage)

    def test_empty_page_has_no_posts(self):
        page = parse_page(_make_page_html())
        assert page.posts == []

    def test_empty_page_has_no_next_token(self):
        page = parse_page(_make_page_html())
        assert page.next_page_token is None

    def test_single_post_parsed(self):
        html = _make_page_html(posts_html=_make_post_html())
        page = parse_page(html)
        assert len(page.posts) == 1

    def test_multiple_posts_parsed(self):
        posts = "".join(
            _make_post_html(
                post_url=f"https://t.me/testchannel/{i}",
                content=f"Post number {i}",
                timestamp=f"2024-01-{i:02d}T12:00:00+00:00",
            )
            for i in range(1, 6)
        )
        page = parse_page(_make_page_html(posts_html=posts))
        assert len(page.posts) == 5

    def test_next_page_token_extracted(self):
        html = _make_page_html(posts_html=_make_post_html(), before_token="35")
        page = parse_page(html)
        assert page.next_page_token == "35"

    def test_no_pagination_link_gives_none_token(self):
        html = _make_page_html(posts_html=_make_post_html())
        page = parse_page(html)
        assert page.next_page_token is None

    def test_post_content_round_trip(self):
        html = _make_page_html(posts_html=_make_post_html(content="OSINT report"))
        page = parse_page(html)
        assert page.posts[0].content == "OSINT report"

    def test_post_timestamp_round_trip(self):
        html = _make_page_html(posts_html=_make_post_html(timestamp="2023-11-20T16:45:00+00:00"))
        page = parse_page(html)
        ts = page.posts[0].timestamp
        assert ts is not None
        assert ts.year == 2023
        assert ts.month == 11
        assert ts.day == 20

    def test_completely_empty_html(self):
        page = parse_page("")
        assert page.posts == []
        assert page.next_page_token is None
