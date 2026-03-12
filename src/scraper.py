import os
import re
import shutil
import random
import time
import threading
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Optional, TextIO, Tuple, Callable

from my_telegram_scrapper import SimpleScraperClient, SimpleTgPost

# --- Constants ---
ARCHIVE_DIR_NAME: str = "archive"
CUTOFF_DATE: date = date(2022, 1, 1)


# --- File Utilities ---

def archive_old_output_files(base_dir_str: str, log_callback: Callable[[str, str], None]):
    """Moves existing output_*.txt files from the base directory to an archive subfolder."""
    base_dir = Path(base_dir_str)
    archive_path = base_dir / ARCHIVE_DIR_NAME

    try:
        if not archive_path.exists():
            archive_path.mkdir(parents=True, exist_ok=True)
            log_callback(f"Created archive directory: {archive_path}", "INFO")

        output_files = list(base_dir.glob("output_*.txt"))
        if not output_files:
            log_callback("No previous output files found to archive.", "INFO")
            return

        log_callback(f"Found {len(output_files)} output file(s) to archive...", "INFO")
        archived_count = 0
        for file_path in output_files:
            try:
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                random_num = random.randint(1000, 9999)
                archive_name = f"{file_path.stem}_{timestamp_str}_{random_num}{file_path.suffix}"
                shutil.move(str(file_path), str(archive_path / archive_name))
                log_callback(f"  Archived {file_path.name} to {archive_name}", "DEBUG")
                archived_count += 1
            except Exception as e:
                log_callback(f"Error archiving file {file_path.name}: {e}", "ERROR")

        log_callback(f"Archiving complete. Moved {archived_count} file(s).", "INFO")

    except Exception as e:
        log_callback(f"Error during archiving: {e}", "ERROR")


def load_channels(channellist_file: str, log_callback: Callable[[str, str], None]) -> List[str]:
    """Loads and validates channel names from the given text file."""
    channels: List[str] = []
    file_path = Path(channellist_file)

    if not file_path.is_file():
        log_callback(f"Channel list file not found: {channellist_file}", "ERROR")
        raise FileNotFoundError(f"Channel list file not found: {channellist_file}")

    try:
        with file_path.open("r", encoding="utf-8") as infile:
            for line_num, line in enumerate(infile, 1):
                original_line = line
                line = line.strip().rstrip('/')
                if not line or line.startswith('#'):
                    continue
                channel_name = line.rsplit('/', 1)[-1] if '/' in line else line
                if channel_name and re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,}$', channel_name):
                    if channel_name not in channels:
                        channels.append(channel_name)
                else:
                    log_callback(f"Skipping invalid entry on line {line_num}: '{original_line.strip()}'", "WARN")

        log_callback(f"Loaded {len(channels)} unique, valid channel names from {file_path.name}.", "INFO")
        if not channels:
            log_callback("The channel list file is empty or contains no valid channel names.", "ERROR")
            raise ValueError(f"No valid channel names found in {file_path.name}.")
        return channels

    except OSError as e:
        log_callback(f"Error reading channel list file {channellist_file}: {e}", "ERROR")
        raise RuntimeError(f"Error reading channel list file: {e}") from e


# --- Scraping Logic ---

def _determine_date_range(
    mode: str, target_date: Optional[date], start_date: Optional[date], end_date: Optional[date]
) -> Tuple[date, date, str]:
    """Determines the effective start/end dates based on the scraping mode."""
    effective_start_date = CUTOFF_DATE
    effective_end_date = date.today()
    log_date_info = ""

    if mode in ['today', 'yesterday', 'specific_date']:
        if target_date is None:
            raise ValueError(f"Target date is required for mode '{mode}'.")
        effective_start_date = effective_end_date = target_date
        log_date_info = f" for date {target_date.strftime('%Y-%m-%d')}"
    elif mode == 'date_range':
        if start_date is None or end_date is None:
            raise ValueError("Start and end dates are required for 'date_range' mode.")
        effective_start_date = max(start_date, CUTOFF_DATE)
        effective_end_date = end_date
        log_date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        if start_date < CUTOFF_DATE:
            log_date_info += f" (effective start: {effective_start_date.strftime('%Y-%m-%d')})"
    elif mode == 'all':
        log_date_info = f" (since {CUTOFF_DATE.strftime('%Y-%m-%d')})"

    if effective_end_date < effective_start_date:
        raise ValueError(
            f"Effective end date ({effective_end_date}) cannot be before start date ({effective_start_date})."
        )
    return effective_start_date, effective_end_date, log_date_info


def _write_post_to_file(handle: TextIO, channel: str, post: SimpleTgPost):
    """Formats and writes a single post to an open file handle."""
    try:
        post_content = re.sub(r'\s{2,}', ' ', post.content or "[No text content]").strip()
        post_time_str = post.timestamp.strftime('%H:%M:%S') if post.timestamp else "[No Time]"
        handle.write(f"{channel} | {post.post_url or '[No URL]'} ({post_time_str}) : {post_content}\n")
    except Exception as e:
        print(f"Error writing post {post.post_url} for channel {channel}: {e}")


def _get_output_file_handle(
    post_date_str: str, output_dir: Path, base_list_name: str,
    open_files: Dict[str, TextIO], output_files_created: List[Path], log_callback: Callable
) -> Optional[TextIO]:
    """Gets or creates the file handle for a specific date."""
    if post_date_str in open_files:
        return open_files[post_date_str]

    file_path = output_dir / f"output_{base_list_name}_{post_date_str}.txt"
    try:
        handle = open(file_path, "a", encoding="utf-8")
        if file_path.stat().st_size == 0:
            handle.write(f"### Posts from {post_date_str} (List: {base_list_name})\n\n")
        open_files[post_date_str] = handle
        if file_path not in output_files_created:
            output_files_created.append(file_path)
            log_callback(f"Opened output file: {file_path.name}", "DEBUG")
        return handle
    except OSError as e:
        log_callback(f"Failed to open output file {file_path}: {e}", "ERROR")
        return None


def _process_scraped_post(
    post: SimpleTgPost, channel: str, mode: str,
    effective_start_date: date, effective_end_date: date,
    output_dir: Path, base_list_name: str,
    open_files: Dict[str, TextIO], output_files_created: List[Path],
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]],
    log_callback: Callable
) -> bool:
    """Checks if a post matches date criteria and writes it to the appropriate file/list."""
    if not post.timestamp:
        return False

    current_post_date = post.timestamp.date()
    if current_post_date < CUTOFF_DATE:
        return False

    if mode == 'all':
        in_range = True
    elif mode == 'date_range':
        in_range = effective_start_date <= current_post_date <= effective_end_date
    else:  # today, yesterday, specific_date
        in_range = current_post_date == effective_start_date

    if not in_range:
        return False

    if mode in ['all', 'date_range']:
        post_date_str = current_post_date.strftime("%Y-%m-%d")
        handle = _get_output_file_handle(
            post_date_str, output_dir, base_list_name, open_files, output_files_created, log_callback
        )
        if handle:
            _write_post_to_file(handle, channel, post)
            return True
    else:
        all_posts_for_specific_date.append((channel, post))
        return True

    return False


def _scrape_single_channel(
    client: SimpleScraperClient, channel: str, mode: str,
    effective_start_date: date, effective_end_date: date,
    log_callback: Callable, stop_event: threading.Event,
    output_dir: Path, base_list_name: str,
    open_files: Dict[str, TextIO], output_files_created: List[Path],
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]]
) -> int:
    """Scrapes posts for a single channel, handling pagination and date filtering."""
    next_page_token: Optional[str] = None
    pages_checked = 0
    processed_posts_count = 0
    last_oldest_date_on_page: Optional[date] = None

    log_callback(f"Starting channel: {channel}", "DEBUG")

    while True:
        if stop_event.is_set():
            log_callback(f"Stop signal received, interrupting channel {channel}.", "WARN")
            break

        pages_checked += 1
        log_callback(f"  Fetching page {pages_checked} for {channel} (Token: {next_page_token or 'None'})...", "DEBUG")

        try:
            page_data = client.get_channel_page(channel, before_token=next_page_token)
        except Exception as e:
            log_callback(f"Error fetching page {pages_checked} for {channel}: {e}", "ERROR")
            break

        if not page_data or not page_data.posts:
            log_callback(f"  No more posts found for {channel} on page {pages_checked}.", "INFO")
            break

        oldest_post_date_this_page: Optional[date] = None
        posts_processed_this_page = 0

        for post in page_data.posts:
            if post.timestamp:
                current_post_date = post.timestamp.date()
                if oldest_post_date_this_page is None or current_post_date < oldest_post_date_this_page:
                    oldest_post_date_this_page = current_post_date
                if _process_scraped_post(
                    post, channel, mode, effective_start_date, effective_end_date,
                    output_dir, base_list_name, open_files, output_files_created,
                    all_posts_for_specific_date, log_callback
                ):
                    posts_processed_this_page += 1

        if posts_processed_this_page > 0:
            log_callback(f"  Processed {posts_processed_this_page} matching posts from page {pages_checked}.", "DEBUG")

        processed_posts_count += posts_processed_this_page
        last_oldest_date_on_page = oldest_post_date_this_page

        next_page_token = page_data.next_page_token
        if not next_page_token:
            log_callback(f"  End of channel history reached for {channel}.", "INFO")
            break

        if last_oldest_date_on_page and last_oldest_date_on_page < effective_start_date:
            log_callback(
                f"  Oldest post ({last_oldest_date_on_page}) is before target start date. Stopping pagination for {channel}.",
                "INFO"
            )
            break

        if pages_checked > 500:
            log_callback(f"Warning: Exceeded 500 pages for channel {channel}. Stopping pagination.", "WARN")
            break

    log_callback(f"Finished channel {channel}. Found {processed_posts_count} matching posts.", "INFO")
    return processed_posts_count


def scrape_channels(
    channellist_file: str, mode: str,
    target_date: Optional[date], start_date: Optional[date], end_date: Optional[date],
    log_callback: Callable, stop_event: threading.Event,
    output_dir: Path
) -> List[Path]:
    """Scrapes posts from channels listed in a file based on mode and date criteria."""
    output_files_created: List[Path] = []
    base_list_name = Path(channellist_file).stem

    try:
        effective_start_date, effective_end_date, log_date_info = _determine_date_range(
            mode, target_date, start_date, end_date
        )
    except ValueError as e:
        log_callback(f"Date range error: {e}", "ERROR")
        raise

    log_callback(f"Starting scraping process. Mode: '{mode}'{log_date_info}", "INFO")

    channels = load_channels(channellist_file, log_callback)

    open_files: Dict[str, TextIO] = {}
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]] = []
    total_processed_posts = 0

    try:
        with SimpleScraperClient() as client:
            log_callback(f"Processing {len(channels)} channels from {Path(channellist_file).name}...", "INFO")
            for i, channel in enumerate(channels):
                if stop_event.is_set():
                    log_callback("Stop signal received. Aborting channel processing.", "WARN")
                    break

                log_callback(f"--- Channel {i+1}/{len(channels)}: {channel} ---", "INFO")
                total_processed_posts += _scrape_single_channel(
                    client, channel, mode, effective_start_date, effective_end_date,
                    log_callback, stop_event, output_dir, base_list_name,
                    open_files, output_files_created, all_posts_for_specific_date
                )
    except Exception as e:
        log_callback(f"Critical error during scraping: {e}", "ERROR")
        raise RuntimeError(f"Scraping failed: {e}") from e
    finally:
        for date_str, handle in open_files.items():
            try:
                if handle and not handle.closed:
                    handle.close()
            except Exception as e:
                log_callback(f"Error closing file for date {date_str}: {e}", "ERROR")

    if mode in ['today', 'yesterday', 'specific_date'] and all_posts_for_specific_date and target_date:
        output_file_path = output_dir / f"output_{base_list_name}_{target_date.strftime('%Y-%m-%d')}.txt"
        log_callback(f"Writing {len(all_posts_for_specific_date)} collected posts to {output_file_path.name}...", "INFO")
        try:
            all_posts_for_specific_date.sort(key=lambda item: item[1].timestamp or datetime.min)
            with open(output_file_path, "w", encoding="utf-8") as outfile:
                outfile.write(f"### Posts from {target_date.strftime('%Y-%m-%d')} (List: {base_list_name})\n\n")
                for channel_name, post in all_posts_for_specific_date:
                    _write_post_to_file(outfile, channel_name, post)
            if output_file_path not in output_files_created:
                output_files_created.append(output_file_path)
            log_callback(f"Successfully wrote: {output_file_path.name}", "INFO")
        except OSError as e:
            log_callback(f"Failed to write output file {output_file_path.name}: {e}", "ERROR")

    if stop_event.is_set():
        log_callback(f"Scraping interrupted. Processed {total_processed_posts} posts into {len(output_files_created)} files.", "WARN")
    elif total_processed_posts == 0:
        log_callback(f"Scraping finished. No posts found matching the specified criteria{log_date_info}.", "INFO")
    else:
        log_callback(f"Scraping finished successfully. Processed {total_processed_posts} posts into {len(output_files_created)} files.", "INFO")

    return output_files_created


def run_scraping(
    channellist_file: str, mode: str,
    target_date: Optional[date], start_date: Optional[date], end_date: Optional[date],
    log_callback: Callable[[str, str], None], stop_event: threading.Event, base_dir: str
) -> List[str]:
    """Entry point called by the GUI thread. Archives old files then runs scraping."""
    base_dir_path = Path(base_dir)

    try:
        archive_old_output_files(str(base_dir_path), log_callback)

        if stop_event.is_set():
            log_callback("Process stopped during archiving phase.", "WARN")
            return []

        log_callback("Archiving complete. Starting channel processing...", "INFO")
        output_files = scrape_channels(
            channellist_file=channellist_file,
            mode=mode,
            target_date=target_date,
            start_date=start_date,
            end_date=end_date,
            log_callback=log_callback,
            stop_event=stop_event,
            output_dir=base_dir_path,
        )
        return [str(f) for f in output_files]

    except (FileNotFoundError, ValueError, RuntimeError, NameError, ImportError) as e:
        log_callback(f"Scraping process failed: {e}", "ERROR")
        raise
    except Exception as e:
        log_callback(f"An unexpected critical error occurred: {e}", "ERROR")
        raise RuntimeError(f"Unexpected error: {e}") from e
