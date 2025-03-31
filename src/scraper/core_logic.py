import os
import re # Import re
import threading
import time
from datetime import date, datetime
from pathlib import Path # Use pathlib for path operations
from typing import List, Dict, Optional, TextIO, Tuple, Callable, Any # Added Any

# Import client and models from the sibling package
try:
    from my_telegram_scrapper import SimpleScraperClient, SimpleTgPost, ScrapedPage
except ImportError as e:
    # This error should ideally be caught at the application entry point,
    # but raise it here too for clarity if this module is used independently.
    raise ImportError("Could not import from 'my_telegram_scrapper'. Is it installed or in PYTHONPATH?") from e

# Import configuration and utilities
from src.config import CUTOFF_DATE
from src.utils.file_utils import archive_old_output_files, load_channels

# --- Helper Functions ---

def _determine_date_range(
    mode: str, target_date: Optional[date], start_date: Optional[date], end_date: Optional[date]
) -> Tuple[date, date, str]:
    """
    Determines the effective start and end dates for scraping based on the mode.
    Also generates a string describing the date criteria for logging.

    Returns:
        A tuple containing (effective_start_date, effective_end_date, log_date_info_string).
    Raises:
        ValueError if required dates for a mode are missing or invalid range.
    """
    log_date_info = ""
    # Default range is from CUTOFF_DATE up to today
    effective_start_date = CUTOFF_DATE
    effective_end_date = date.today()

    if mode in ['today', 'yesterday', 'specific_date']:
        if target_date is None:
            raise ValueError(f"Target date is required for mode '{mode}'.")
        # For single-date modes, start and end are the same
        effective_start_date = target_date
        effective_end_date = target_date
        log_date_info = f" for date {target_date.strftime('%Y-%m-%d')}"
    elif mode == 'date_range':
        if start_date is None or end_date is None:
            raise ValueError("Start and end dates are required for 'date_range' mode.")
        # Ensure range start is not before the absolute cutoff
        effective_start_date = max(start_date, CUTOFF_DATE)
        effective_end_date = end_date
        log_date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        # Add effective range info if start date was adjusted by cutoff
        if start_date < CUTOFF_DATE:
             log_date_info += f" (effective start: {effective_start_date.strftime('%Y-%m-%d')})"
    elif mode == 'all':
        # Uses the default range (CUTOFF_DATE to today)
        log_date_info = f" (since {CUTOFF_DATE.strftime('%Y-%m-%d')})"
        # effective_start_date and effective_end_date remain as defaults

    # Final validation: end date should not be before start date (can happen with cutoff adjustment)
    if effective_end_date < effective_start_date:
         raise ValueError(f"Effective end date ({effective_end_date.strftime('%Y-%m-%d')}) cannot be before effective start date ({effective_start_date.strftime('%Y-%m-%d')}).")

    return effective_start_date, effective_end_date, log_date_info


def _write_post_to_file(handle: TextIO, channel: str, post: SimpleTgPost):
    """Formats and writes a single post to an open file handle."""
    try:
        post_content = post.content or "[No text content]"
        # Clean potential multiple newlines or excessive whitespace
        post_content = re.sub(r'\s{2,}', ' ', post_content).strip() # Use re.sub

        post_url_str = post.post_url or "[No URL]"
        post_time_str = post.timestamp.strftime('%H:%M:%S') if post.timestamp else "[No Time]"
        # Format: ChannelName | URL (HH:MM:SS) : Content
        post_info = f"{channel} | {post_url_str} ({post_time_str}) : {post_content}\n"
        handle.write(post_info)
    except Exception as e:
        # Log error but don't stop the whole process for one write failure
        # Ideally use log_callback if available, else print
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
        # Use 'a' mode (append)
        handle = open(file_path, "a", encoding="utf-8")
        # Write header only if the file is newly created (or empty)
        if file_path.stat().st_size == 0:
            handle.write(f"### Posts from {post_date_str} (List: {base_list_name})\n\n")
        open_files[post_date_str] = handle
        # Track the file path if newly opened/created
        if file_path not in output_files_created:
            output_files_created.append(file_path)
            log_callback(f"Opened output file: {file_path.name}", "DEBUG") # Debug level log
        return handle
    except OSError as e:
        log_callback(f"Failed to open/write header to output file {file_path}: {e}", "ERROR")
        return None


def _process_scraped_post(
    post: SimpleTgPost, channel: str, mode: str,
    effective_start_date: date, effective_end_date: date,
    output_dir: Path, base_list_name: str,
    open_files: Dict[str, TextIO], output_files_created: List[Path],
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]],
    log_callback: Callable
) -> bool:
    """
    Checks if a post matches date criteria and writes it to the appropriate file/list.
    Returns True if the post was processed, False otherwise.
    """
    if not post.timestamp:
        return False # Cannot process without a timestamp

    current_post_date = post.timestamp.date()

    # --- Date Filtering ---
    # 1. Check against absolute CUTOFF_DATE (skip if older)
    if current_post_date < CUTOFF_DATE:
        return False

    # 2. Check against mode-specific date range
    is_within_target_range = False
    if mode == 'all':
        # Already passed CUTOFF check, so it's valid for 'all'
        is_within_target_range = True
    elif mode == 'date_range':
        # Check if within the effective start/end dates
        is_within_target_range = (effective_start_date <= current_post_date <= effective_end_date)
    elif mode in ['today', 'yesterday', 'specific_date']:
        # Check if it matches the single target date (start date = end date = target date)
        is_within_target_range = (current_post_date == effective_start_date)

    if not is_within_target_range:
        return False # Post date does not match the required criteria for the mode

    # --- Process Matching Post ---
    processed = False
    if mode == 'all' or mode == 'date_range':
        # Write directly to the file corresponding to the post's date
        post_date_str = current_post_date.strftime("%Y-%m-%d")
        handle = _get_output_file_handle(
            post_date_str, output_dir, base_list_name,
            open_files, output_files_created, log_callback
        )
        if handle:
            _write_post_to_file(handle, channel, post)
            processed = True
        # else: Error getting handle was logged by _get_output_file_handle

    elif mode in ['today', 'yesterday', 'specific_date']:
        # Collect posts for single-date modes to write later (allows sorting)
        all_posts_for_specific_date.append((channel, post)) # Store channel name with post
        processed = True

    return processed


def _scrape_single_channel(
    client: SimpleScraperClient, channel: str, mode: str,
    effective_start_date: date, effective_end_date: date,
    log_callback: Callable, stop_event: threading.Event,
    output_dir: Path, base_list_name: str,
    open_files: Dict[str, TextIO], output_files_created: List[Path],
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]]
) -> int:
    """
    Scrapes posts for a single channel, handling pagination and date filtering.

    Returns:
        The number of posts successfully processed for this channel matching criteria.
    """
    next_page_token: Optional[str] = None
    pages_checked = 0
    processed_posts_count = 0 # Posts processed *for this channel* matching criteria
    stop_channel_pagination = False
    last_oldest_date_on_page: Optional[date] = None # Track oldest date seen

    log_callback(f"Starting channel: {channel}", "DEBUG")

    while not stop_channel_pagination:
        if stop_event.is_set():
            log_callback(f"Stop signal received, interrupting channel {channel}.", "WARN")
            break # Break inner loop (pagination)

        pages_checked += 1
        log_callback(f"  Fetching page {pages_checked} for {channel} (Token: {next_page_token or 'None'})...", "DEBUG")

        # --- Fetch Page ---
        try:
            page_data = client.get_channel_page(channel, before_token=next_page_token)
        except Exception as fetch_e: # Catch errors during fetch/parse at client level
            log_callback(f"Error fetching/parsing page {pages_checked} for {channel}: {fetch_e}", "ERROR")
            stop_channel_pagination = True # Stop processing this channel on error
            continue # Skip to next channel or finish

        if not page_data or not page_data.posts:
            log_callback(f"  No more posts found or page error for {channel} on page {pages_checked}.", "INFO")
            stop_channel_pagination = True
            continue

        # --- Process Posts on Page ---
        posts_on_page = page_data.posts
        oldest_post_date_this_page: Optional[date] = None
        posts_processed_this_page = 0

        for post in posts_on_page:
             if post.timestamp:
                 current_post_date = post.timestamp.date()
                 # Update oldest date seen on this specific page
                 if oldest_post_date_this_page is None or current_post_date < oldest_post_date_this_page:
                     oldest_post_date_this_page = current_post_date

                 # Process the post (checks dates, writes/collects)
                 if _process_scraped_post(
                     post, channel, mode, effective_start_date, effective_end_date,
                     output_dir, base_list_name, open_files, output_files_created,
                     all_posts_for_specific_date, log_callback
                 ):
                     posts_processed_this_page += 1

        if posts_processed_this_page > 0:
             log_callback(f"  Processed {posts_processed_this_page} matching posts from page {pages_checked}.", "DEBUG")
        # Log if posts existed but none matched criteria for this specific page
        elif posts_on_page:
             log_callback(f"  No posts on page {pages_checked} matched date criteria for mode '{mode}'.", "DEBUG")

        processed_posts_count += posts_processed_this_page
        last_oldest_date_on_page = oldest_post_date_this_page # Store for pagination logic

        # --- Pagination Stop Conditions ---
        next_page_token = page_data.next_page_token
        if not next_page_token:
            log_callback(f"  End of channel history reached for {channel} (no next page token).", "INFO")
            stop_channel_pagination = True
            continue

        # Stop if the oldest post found on the page is before the required start date
        if last_oldest_date_on_page:
             if last_oldest_date_on_page < effective_start_date:
                  log_callback(f"  Oldest post on page ({last_oldest_date_on_page.strftime('%Y-%m-%d')}) is before target start date ({effective_start_date.strftime('%Y-%m-%d')}). Stopping pagination for {channel}.", "INFO")
                  stop_channel_pagination = True
                  continue
        # Add a safety break if pages_checked gets excessively high?
        if pages_checked > 500: # Arbitrary limit to prevent infinite loops on weird pages
             log_callback(f"Warning: Exceeded 500 pages for channel {channel}. Stopping pagination.", "WARN")
             stop_channel_pagination = True
             continue

        # Optional: Short delay between page requests
        # time.sleep(0.1) # Be mindful of rate limiting

    log_callback(f"Finished channel {channel}. Found {processed_posts_count} matching posts.", "INFO")
    return processed_posts_count

# --- Main Scraping Function ---
def scrape_channels(
    channellist_file: str, mode: str,
    target_date: Optional[date], start_date: Optional[date], end_date: Optional[date],
    log_callback: Callable, stop_event: threading.Event,
    output_dir: Path
) -> List[Path]:
    """
    Scrapes posts from channels listed in a file based on mode and date criteria.

    Args:
        channellist_file: Path to the file containing channel names/URLs.
        mode: Scraping mode ('today', 'yesterday', 'specific_date', 'date_range', 'all').
        target_date: The specific date for single-date modes.
        start_date: Start date for range mode.
        end_date: End date for range mode.
        log_callback: Function to call for logging messages to the GUI/console.
        stop_event: Threading event to signal stopping the process.
        output_dir: Path object for the directory to save output files.

    Returns:
        A list of Path objects for the output files created or updated.
    Raises:
        ValueError, FileNotFoundError, RuntimeError on critical errors.
    """
    output_files_created: List[Path] = []
    # Get the base name of the channel list file (e.g., "proRuChannels")
    base_list_name = Path(channellist_file).stem

    try:
        effective_start_date, effective_end_date, log_date_info = _determine_date_range(
            mode, target_date, start_date, end_date
        )
    except ValueError as e:
        log_callback(f"Date range error: {e}", "ERROR")
        raise e # Re-raise for the caller (GUI thread)

    log_callback(f"Starting scraping process. Mode: '{mode}'{log_date_info}", "INFO")
    log_callback(f"Effective date range: {effective_start_date.strftime('%Y-%m-%d')} to {effective_end_date.strftime('%Y-%m-%d')}", "DEBUG")

    # Load channels (handles its own file errors)
    channels = load_channels(channellist_file, log_callback)
    if not channels: # load_channels should raise error if file empty/not found, but double-check
         log_callback("Channel list is empty or could not be loaded.", "ERROR")
         raise ValueError("Channel list is empty.") # Raise error to stop process

    # Dictionary to hold open file handles {date_str: file_handle} for range/all modes
    open_files: Dict[str, TextIO] = {}
    # List to store posts for single-date modes before writing
    all_posts_for_specific_date: List[Tuple[str, SimpleTgPost]] = []
    total_processed_posts = 0

    try:
        # Use the client as a context manager
        with SimpleScraperClient() as client:
            log_callback(f"Processing {len(channels)} channels from {Path(channellist_file).name}...", "INFO")
            for i, channel in enumerate(channels):
                if stop_event.is_set():
                    log_callback("Stop signal received. Aborting channel processing.", "WARN")
                    break # Break outer loop (channel iteration)

                log_callback(f"--- Channel {i+1}/{len(channels)}: {channel} ---", "INFO")

                # Scrape the current channel
                processed_count = _scrape_single_channel(
                    client, channel, mode, effective_start_date, effective_end_date,
                    log_callback, stop_event, output_dir, base_list_name,
                    open_files, output_files_created, all_posts_for_specific_date
                )
                total_processed_posts += processed_count

    except Exception as client_error:
        # Catch unexpected errors during client usage or scraping loop
        log_callback(f"Critical error during scraping: {client_error}", "ERROR")
        # Raise a runtime error to signal failure to the calling thread
        raise RuntimeError(f"Scraping failed due to an unexpected error: {client_error}") from client_error
    finally:
        # --- Cleanup: Close all files opened in range/all mode ---
        if open_files:
            log_callback(f"Closing {len(open_files)} output files...", "INFO")
            closed_count = 0
            for date_str, handle in open_files.items():
                try:
                    if handle and not handle.closed:
                         handle.close()
                         closed_count += 1
                except Exception as close_e:
                    log_callback(f"Error closing file for date {date_str}: {close_e}", "ERROR")
            log_callback(f"Closed {closed_count} files.", "DEBUG")

    # --- Write collected posts for single-date modes ---
    if mode in ['today', 'yesterday', 'specific_date'] and all_posts_for_specific_date:
        if target_date is None:
             # This shouldn't happen if date validation passed, but check defensively
             log_callback("Cannot write single-date file: Target date is missing.", "ERROR")
        else:
             output_file_path = output_dir / f"output_{base_list_name}_{target_date.strftime('%Y-%m-%d')}.txt"
             log_callback(f"Writing {len(all_posts_for_specific_date)} collected posts to {output_file_path.name}...", "INFO")
             try:
                 # Sort posts by timestamp before writing for chronological order
                 all_posts_for_specific_date.sort(
                     key=lambda item: item[1].timestamp or datetime.min # Sort by post timestamp
                 )
                 # Use 'w' mode (write/overwrite) for single-date files
                 with open(output_file_path, "w", encoding="utf-8") as outfile:
                     outfile.write(f"### Posts from {target_date.strftime('%Y-%m-%d')} (List: {base_list_name})\n\n")
                     for channel_name, post in all_posts_for_specific_date:
                         _write_post_to_file(outfile, channel_name, post)

                 # Add the file path to the list of created files if not already present
                 if output_file_path not in output_files_created:
                     output_files_created.append(output_file_path)
                 log_callback(f"Successfully wrote single-date file: {output_file_path.name}", "INFO")
             except OSError as write_e:
                 log_callback(f"Failed to write output file {output_file_path.name}: {write_e}", "ERROR")
                 # Optionally remove from created list if write failed partway?
                 if output_file_path in output_files_created:
                     output_files_created.remove(output_file_path)

    # --- Final Logging ---
    total_files = len(output_files_created)
    if stop_event.is_set():
         log_callback(f"Scraping interrupted. Processed {total_processed_posts} posts into {total_files} files before stopping.", "WARN")
    elif total_processed_posts == 0: # Check if *any* posts matching criteria were found across all channels
        log_callback(f"Scraping finished. No posts found matching the specified criteria{log_date_info}.", "INFO")
    else:
        log_callback(f"Scraping finished successfully. Processed {total_processed_posts} posts into {total_files} files.", "INFO")

    return output_files_created


# --- Runner Function (called by the GUI thread) ---
def run_scraping(
    channellist_file: str, mode: str,
    target_date: Optional[date], start_date: Optional[date], end_date: Optional[date],
    log_callback: Callable[[str, str], None], stop_event: threading.Event, base_dir: str
) -> List[str]:
    """
    Entry point called by the GUI thread. Handles setup (archiving) and calls the main scraping logic.

    Args:
        base_dir: The application's base directory (string). Other args are as in scrape_channels.
        log_callback: Adjusted signature for level

    Returns:
        A list of string paths for the output files created or updated.
    Raises:
        Exceptions caught during setup or scraping, to be handled by the calling GUI thread.
    """
    output_files: List[Path] = [] # List of Path objects
    base_dir_path = Path(base_dir)
    output_dir = base_dir_path # Output files go directly into the base directory

    try:
        # 1. Archive existing output files before starting
        archive_old_output_files(str(base_dir_path), log_callback) # Pass base_dir as string if util expects it

        if stop_event.is_set():
             log_callback("Process stopped during archiving phase.", "WARN")
             return [] # Return empty list if stopped early

        # 2. Run the main scraping function
        log_callback("Archiving complete. Starting channel processing...", "INFO")
        output_files = scrape_channels(
            channellist_file=channellist_file,
            mode=mode,
            target_date=target_date,
            start_date=start_date,
            end_date=end_date,
            log_callback=log_callback, # Pass the callback directly
            stop_event=stop_event,
            output_dir=output_dir # Pass the Path object
        )
        # Convert Path objects back to strings for the GUI handler if needed
        return [str(f) for f in output_files]

    except (FileNotFoundError, ValueError, RuntimeError, NameError, ImportError) as e:
        # Log errors originating from setup or scraping logic
        log_callback(f"Scraping process failed: {e}", "ERROR")
        # Re-raise the exception to be caught by the calling thread (GUI)
        # This allows the GUI to show the specific error message.
        raise e
    except Exception as e:
        # Log unexpected critical errors during the overall process
        log_callback(f"An unexpected critical error occurred in run_scraping: {e}", "ERROR")
        # Optionally log traceback here
        # import traceback
        # log_callback(traceback.format_exc(), "ERROR")
        # Wrap in a RuntimeError for consistent handling by the GUI
        raise RuntimeError(f"Unexpected error during scraping execution: {e}") from e