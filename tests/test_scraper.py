"""Tests for src.scraper – channel loading, date logic, post writing, post processing."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import pytest
import threading
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from my_telegram_scrapper.models import SimpleTgPost, SimpleTgAuthor, ScrapedPage
from src.scraper import (
    ARCHIVE_DIR_NAME,
    CUTOFF_DATE,
    archive_old_output_files,
    load_channels,
    run_scraping,
    _determine_date_range,
    _write_post_to_file,
    _process_scraped_post,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _noop_log(msg: str, level: str = "INFO"):
    """Discard log messages during tests."""
    pass


def _make_post(
    content: str = "Test content",
    post_url: str = "https://t.me/ch/1",
    timestamp: datetime = None,
    views: str = "10",
) -> SimpleTgPost:
    if timestamp is None:
        timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return SimpleTgPost(
        post_id=1,
        post_url=post_url,
        content=content,
        timestamp=timestamp,
        views=views,
        author=SimpleTgAuthor(username="ch", display_name="Channel", profile_url="https://t.me/ch"),
    )


# ---------------------------------------------------------------------------
# load_channels
# ---------------------------------------------------------------------------

class TestLoadChannels:
    def _write_list(self, lines: list, tmp_path: Path) -> str:
        p = tmp_path / "channels.txt"
        p.write_text("\n".join(lines), encoding="utf-8")
        return str(p)

    def test_loads_plain_usernames(self, tmp_path):
        path = self._write_list(["testchannel", "osintbees"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert "testchannel" in channels
        assert "osintbees" in channels

    def test_extracts_username_from_full_url(self, tmp_path):
        path = self._write_list(["https://t.me/testchannel"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels == ["testchannel"]

    def test_skips_comments(self, tmp_path):
        path = self._write_list(["# this is a comment", "validchannel"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels == ["validchannel"]

    def test_skips_blank_lines(self, tmp_path):
        path = self._write_list(["validchannel", "", "  "], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels == ["validchannel"]

    def test_deduplicates_channels(self, tmp_path):
        path = self._write_list(["testchannel", "testchannel", "https://t.me/testchannel"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels.count("testchannel") == 1

    def test_strips_trailing_slash(self, tmp_path):
        path = self._write_list(["https://t.me/testchannel/"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels == ["testchannel"]

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_channels(str(tmp_path / "nonexistent.txt"), _noop_log)

    def test_empty_file_raises_value_error(self, tmp_path):
        path = self._write_list([], tmp_path)
        with pytest.raises(ValueError):
            load_channels(path, _noop_log)

    def test_invalid_entries_are_skipped(self, tmp_path):
        # Too short (< 5 chars after first letter), starts with digit, etc.
        path = self._write_list(["ab", "1invalid", "validchannel"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert channels == ["validchannel"]

    def test_valid_channel_with_underscores(self, tmp_path):
        path = self._write_list(["osint_news_channel"], tmp_path)
        channels = load_channels(path, _noop_log)
        assert "osint_news_channel" in channels


# ---------------------------------------------------------------------------
# _determine_date_range
# ---------------------------------------------------------------------------

class TestDetermineDateRange:
    def test_today_mode_uses_today(self):
        today = date.today()
        start, end, info = _determine_date_range("today", today, None, None)
        assert start == today
        assert end == today

    def test_yesterday_mode_uses_yesterday(self):
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        start, end, info = _determine_date_range("yesterday", yesterday, None, None)
        assert start == yesterday
        assert end == yesterday

    def test_specific_date_mode(self):
        target = date(2024, 6, 15)
        start, end, info = _determine_date_range("specific_date", target, None, None)
        assert start == target
        assert end == target
        assert "2024-06-15" in info

    def test_date_range_mode(self):
        start_d = date(2024, 1, 1)
        end_d = date(2024, 1, 31)
        start, end, info = _determine_date_range("date_range", None, start_d, end_d)
        assert start == start_d
        assert end == end_d
        assert "2024-01-01" in info
        assert "2024-01-31" in info

    def test_date_range_start_before_cutoff_is_clamped(self):
        start_d = date(2020, 1, 1)  # before CUTOFF_DATE
        end_d = date(2024, 1, 1)
        start, end, info = _determine_date_range("date_range", None, start_d, end_d)
        assert start == CUTOFF_DATE
        assert "effective start" in info

    def test_all_mode_uses_cutoff_to_today(self):
        start, end, info = _determine_date_range("all", None, None, None)
        assert start == CUTOFF_DATE
        assert end == date.today()
        assert str(CUTOFF_DATE.year) in info

    def test_today_mode_missing_target_raises(self):
        with pytest.raises(ValueError):
            _determine_date_range("today", None, None, None)

    def test_date_range_missing_dates_raises(self):
        with pytest.raises(ValueError):
            _determine_date_range("date_range", None, date(2024, 1, 1), None)

    def test_log_info_contains_date_for_specific(self):
        target = date(2023, 5, 10)
        _, _, info = _determine_date_range("specific_date", target, None, None)
        assert "2023-05-10" in info


# ---------------------------------------------------------------------------
# _write_post_to_file
# ---------------------------------------------------------------------------

class TestWritePostToFile:
    def test_writes_channel_name(self):
        buf = io.StringIO()
        _write_post_to_file(buf, "mychannel", _make_post())
        assert "mychannel" in buf.getvalue()

    def test_writes_post_url(self):
        buf = io.StringIO()
        _write_post_to_file(buf, "ch", _make_post(post_url="https://t.me/ch/99"))
        assert "https://t.me/ch/99" in buf.getvalue()

    def test_writes_content(self):
        buf = io.StringIO()
        _write_post_to_file(buf, "ch", _make_post(content="Some important news"))
        assert "Some important news" in buf.getvalue()

    def test_writes_timestamp_time(self):
        buf = io.StringIO()
        ts = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        _write_post_to_file(buf, "ch", _make_post(timestamp=ts))
        assert "14:30:00" in buf.getvalue()

    def test_no_timestamp_uses_placeholder(self):
        buf = io.StringIO()
        post = _make_post()
        post.timestamp = None
        _write_post_to_file(buf, "ch", post)
        assert "[No Time]" in buf.getvalue()

    def test_no_content_uses_placeholder(self):
        buf = io.StringIO()
        post = _make_post()
        post.content = None
        _write_post_to_file(buf, "ch", post)
        assert "[No text content]" in buf.getvalue()

    def test_no_url_uses_placeholder(self):
        buf = io.StringIO()
        post = _make_post()
        post.post_url = None
        _write_post_to_file(buf, "ch", post)
        assert "[No URL]" in buf.getvalue()

    def test_line_ends_with_newline(self):
        buf = io.StringIO()
        _write_post_to_file(buf, "ch", _make_post())
        assert buf.getvalue().endswith("\n")

    def test_excess_whitespace_in_content_is_collapsed(self):
        buf = io.StringIO()
        _write_post_to_file(buf, "ch", _make_post(content="word1  word2   word3"))
        line = buf.getvalue()
        assert "word1 word2 word3" in line


# ---------------------------------------------------------------------------
# _process_scraped_post
# ---------------------------------------------------------------------------

class TestProcessScrapedPost:
    def _make_ctx(self, tmp_path: Path):
        """Return (output_dir, open_files, output_files_created, collected_posts)."""
        return tmp_path, {}, [], []

    def _call(self, post, mode, start, end, tmp_path):
        output_dir, open_files, created, collected = self._make_ctx(tmp_path)
        result = _process_scraped_post(
            post=post,
            channel="testchannel",
            mode=mode,
            effective_start_date=start,
            effective_end_date=end,
            output_dir=output_dir,
            base_list_name="testlist",
            open_files=open_files,
            output_files_created=created,
            all_posts_for_specific_date=collected,
            log_callback=_noop_log,
        )
        return result, open_files, created, collected

    # --- today mode ---
    def test_today_matching_post_is_collected(self, tmp_path):
        today = date.today()
        post = _make_post(timestamp=datetime(today.year, today.month, today.day, 12, 0, tzinfo=timezone.utc))
        result, _, _, collected = self._call(post, "today", today, today, tmp_path)
        assert result is True
        assert len(collected) == 1

    def test_today_wrong_date_not_collected(self, tmp_path):
        today = date.today()
        post = _make_post(timestamp=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc))
        result, _, _, collected = self._call(post, "today", today, today, tmp_path)
        assert result is False
        assert collected == []

    # --- specific_date mode ---
    def test_specific_date_matching_post_collected(self, tmp_path):
        target = date(2024, 6, 1)
        post = _make_post(timestamp=datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc))
        result, _, _, collected = self._call(post, "specific_date", target, target, tmp_path)
        assert result is True
        assert len(collected) == 1
        assert collected[0][0] == "testchannel"
        assert collected[0][1] is post

    # --- date_range mode ---
    def test_date_range_matching_post_written_to_file(self, tmp_path):
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        post = _make_post(timestamp=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc))
        result, open_files, created, _ = self._call(post, "date_range", start, end, tmp_path)
        assert result is True
        assert "2024-01-15" in open_files

    def test_date_range_post_outside_range_rejected(self, tmp_path):
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        post = _make_post(timestamp=datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc))
        result, _, _, _ = self._call(post, "date_range", start, end, tmp_path)
        assert result is False

    # --- all mode ---
    def test_all_mode_recent_post_written(self, tmp_path):
        post = _make_post(timestamp=datetime(2024, 5, 10, 8, 0, tzinfo=timezone.utc))
        result, open_files, _, _ = self._call(post, "all", CUTOFF_DATE, date.today(), tmp_path)
        assert result is True
        assert "2024-05-10" in open_files

    def test_all_mode_post_before_cutoff_rejected(self, tmp_path):
        post = _make_post(timestamp=datetime(2021, 12, 31, 23, 59, tzinfo=timezone.utc))
        result, _, _, _ = self._call(post, "all", CUTOFF_DATE, date.today(), tmp_path)
        assert result is False

    # --- no timestamp ---
    def test_post_without_timestamp_is_rejected(self, tmp_path):
        post = _make_post()
        post.timestamp = None
        today = date.today()
        result, _, _, _ = self._call(post, "today", today, today, tmp_path)
        assert result is False

    # --- output file content ---
    def test_output_file_contains_post_content(self, tmp_path):
        start = date(2024, 3, 1)
        end = date(2024, 3, 31)
        post = _make_post(
            content="Urgent breaking news",
            timestamp=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
        )
        _, open_files, _, _ = self._call(post, "date_range", start, end, tmp_path)
        # Flush and check file content
        for handle in open_files.values():
            handle.flush()
        output_file = tmp_path / "output_testlist_2024-03-15.txt"
        assert output_file.exists()
        text = output_file.read_text(encoding="utf-8")
        assert "Urgent breaking news" in text
        assert "testchannel" in text

    def test_output_file_created_in_created_list(self, tmp_path):
        start = date(2024, 3, 1)
        end = date(2024, 3, 31)
        post = _make_post(timestamp=datetime(2024, 3, 5, 10, 0, tzinfo=timezone.utc))
        _, _, created, _ = self._call(post, "date_range", start, end, tmp_path)
        assert len(created) == 1
        assert "2024-03-05" in created[0].name


# ---------------------------------------------------------------------------
# archive_old_output_files
# ---------------------------------------------------------------------------

class TestArchiveOldOutputFiles:
    def test_moves_output_files_to_archive_dir(self, tmp_path):
        (tmp_path / "output_list_2024-01-01.txt").write_text("data")
        archive_old_output_files(str(tmp_path), _noop_log)
        archive_dir = tmp_path / ARCHIVE_DIR_NAME
        assert archive_dir.exists()
        archived = list(archive_dir.glob("output_list_2024-01-01_*.txt"))
        assert len(archived) == 1

    def test_original_file_is_removed_from_base_dir(self, tmp_path):
        (tmp_path / "output_test_2024-02-01.txt").write_text("data")
        archive_old_output_files(str(tmp_path), _noop_log)
        assert not (tmp_path / "output_test_2024-02-01.txt").exists()

    def test_no_output_files_does_not_move_anything(self, tmp_path):
        keep = tmp_path / "somefile.txt"
        keep.write_text("not an output file")
        archive_old_output_files(str(tmp_path), _noop_log)
        # The non-output file must stay where it is
        assert keep.exists()
        # archive dir may or may not be created, but it must contain no output files
        archive_dir = tmp_path / ARCHIVE_DIR_NAME
        if archive_dir.exists():
            assert list(archive_dir.glob("output_*.txt")) == []

    def test_multiple_output_files_all_archived(self, tmp_path):
        for i in range(3):
            (tmp_path / f"output_list_2024-0{i+1}-01.txt").write_text(f"data{i}")
        archive_old_output_files(str(tmp_path), _noop_log)
        archive_dir = tmp_path / ARCHIVE_DIR_NAME
        assert len(list(archive_dir.glob("output_*.txt"))) == 3

    def test_non_output_txt_files_not_touched(self, tmp_path):
        keep = tmp_path / "channels.txt"
        keep.write_text("mychannel")
        (tmp_path / "output_list_2024-01-01.txt").write_text("data")
        archive_old_output_files(str(tmp_path), _noop_log)
        assert keep.exists()

    def test_archived_filename_contains_original_stem(self, tmp_path):
        (tmp_path / "output_mylist_2024-06-01.txt").write_text("data")
        archive_old_output_files(str(tmp_path), _noop_log)
        archive_dir = tmp_path / ARCHIVE_DIR_NAME
        archived = list(archive_dir.glob("output_mylist_2024-06-01_*.txt"))
        assert len(archived) == 1

    def test_empty_directory_is_handled_gracefully(self, tmp_path):
        archive_old_output_files(str(tmp_path), _noop_log)  # should not raise


# ---------------------------------------------------------------------------
# run_scraping
# ---------------------------------------------------------------------------

def _make_scraped_page(posts=None, next_token=None):
    return ScrapedPage(posts=posts or [], next_page_token=next_token)


def _make_channel_file(tmp_path, channels):
    p = tmp_path / "channels.txt"
    p.write_text("\n".join(channels), encoding="utf-8")
    return str(p)


class TestRunScraping:
    def _stop(self):
        e = threading.Event()
        e.set()
        return e

    def _run(self, tmp_path, mode="today", target_date=None, start_date=None,
             end_date=None, stop_event=None, mock_page=None):
        channel_file = _make_channel_file(tmp_path, ["testchannel"])
        if target_date is None and mode in ("today", "yesterday"):
            target_date = date.today()
        if stop_event is None:
            stop_event = threading.Event()
        page = mock_page if mock_page is not None else _make_scraped_page()
        with patch(
            "my_telegram_scrapper.client.SimpleScraperClient.get_channel_page",
            return_value=page,
        ):
            return run_scraping(
                channellist_file=channel_file,
                mode=mode,
                target_date=target_date,
                start_date=start_date,
                end_date=end_date,
                log_callback=_noop_log,
                stop_event=stop_event,
                base_dir=str(tmp_path),
            )

    def test_returns_list_of_strings(self, tmp_path):
        result = self._run(tmp_path)
        assert isinstance(result, list)
        assert all(isinstance(p, str) for p in result)

    def test_stop_before_archiving_returns_empty(self, tmp_path):
        result = self._run(tmp_path, stop_event=self._stop())
        assert result == []

    def test_archives_existing_output_file(self, tmp_path):
        (tmp_path / "output_channels_2024-01-01.txt").write_text("old data")
        self._run(tmp_path)
        assert not (tmp_path / "output_channels_2024-01-01.txt").exists()
        archived = list((tmp_path / ARCHIVE_DIR_NAME).glob("output_*.txt"))
        assert len(archived) == 1

    def test_empty_channel_page_produces_no_output_files(self, tmp_path):
        result = self._run(tmp_path, mode="today")
        assert result == []

    def test_matching_post_creates_output_file(self, tmp_path):
        today = date.today()
        post = _make_post(
            timestamp=datetime(today.year, today.month, today.day, 10, 0, tzinfo=timezone.utc)
        )
        page = _make_scraped_page(posts=[post])
        result = self._run(tmp_path, mode="today", target_date=today, mock_page=page)
        assert len(result) == 1
        assert os.path.exists(result[0])

    def test_invalid_channel_file_raises_file_not_found(self, tmp_path):
        stop = threading.Event()
        with pytest.raises(FileNotFoundError):
            run_scraping(
                channellist_file=str(tmp_path / "nonexistent.txt"),
                mode="today",
                target_date=date.today(),
                start_date=None,
                end_date=None,
                log_callback=_noop_log,
                stop_event=stop,
                base_dir=str(tmp_path),
            )

    def test_bad_date_range_raises_value_error(self, tmp_path):
        channel_file = _make_channel_file(tmp_path, ["testchannel"])
        stop = threading.Event()
        with pytest.raises(ValueError):
            run_scraping(
                channellist_file=channel_file,
                mode="date_range",
                target_date=None,
                start_date=None,  # missing required dates
                end_date=None,
                log_callback=_noop_log,
                stop_event=stop,
                base_dir=str(tmp_path),
            )
