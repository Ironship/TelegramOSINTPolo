import os
import glob
import shutil
import random
import time
import re
from pathlib import Path # Use pathlib for easier path operations
from typing import List, Callable, Any # Added Any

from src.config import ARCHIVE_DIR_NAME

def archive_old_output_files(base_dir_str: str, log_callback: Callable[[str, str], None]):
    """
    Moves existing output_*.txt files from the base directory to an archive subfolder.
    """
    base_dir = Path(base_dir_str)
    archive_path = base_dir / ARCHIVE_DIR_NAME

    try:
        # Create archive directory if it doesn't exist
        archive_created = False
        if not archive_path.exists():
             archive_path.mkdir(parents=True, exist_ok=True)
             archive_created = True
        if archive_created and archive_path.exists(): # Check creation
            log_callback(f"Created archive directory: {archive_path}", "INFO")

        # Find output files in the base directory using pathlib's glob
        # Pattern: output_ followed by any characters until .txt
        output_files = list(base_dir.glob("output_*.txt"))

        if not output_files:
            log_callback("No previous output files found to archive.", "INFO")
            return

        log_callback(f"Found {len(output_files)} output file(s) to archive...", "INFO")
        archived_count = 0
        for file_path in output_files:
            try:
                # Create a unique archive filename
                base_name = file_path.stem # Name without extension
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                random_num = random.randint(1000, 9999)
                # Keep the original extension (.txt)
                archive_name = f"{base_name}_{timestamp_str}_{random_num}{file_path.suffix}"
                destination_path = archive_path / archive_name

                # Move the file
                shutil.move(str(file_path), str(destination_path))
                log_callback(f"  Archived {file_path.name} to {archive_name}", "DEBUG") # Debug level
                archived_count += 1
            except OSError as e:
                log_callback(f"Error archiving file {file_path.name}: {e}", "ERROR")
            except Exception as e: # Catch other potential errors during move/naming
                 log_callback(f"Unexpected error archiving {file_path.name}: {e}", "ERROR")

        log_callback(f"Archiving complete. Moved {archived_count} file(s).", "INFO")

    except OSError as e:
        log_callback(f"Error creating or accessing archive directory {archive_path}: {e}", "ERROR")
    except Exception as e:
        log_callback(f"General error during archiving process: {e}", "ERROR")


def load_channels(channellist_file: str, log_callback: Callable[[str, str], None]) -> List[str]:
    """
    Loads and validates channel names/URLs from the given text file.
    Extracts the channel username (part after the last '/').

    Returns:
        A list of valid channel usernames.
    Raises:
        FileNotFoundError if the file doesn't exist.
        ValueError if the file contains no valid channel names.
        RuntimeError for other read errors.
    """
    channels: List[str] = []
    file_path = Path(channellist_file)

    if not file_path.is_file():
         log_callback(f"Channel list file not found: {channellist_file}", "ERROR")
         raise FileNotFoundError(f"Channel list file not found: {channellist_file}")

    try:
        with file_path.open("r", encoding="utf-8") as infile:
            for line_num, line in enumerate(infile, 1):
                original_line = line # Keep original for logging errors
                line = line.strip()
                if not line or line.startswith('#'): # Skip empty lines and comments
                    continue

                # Remove trailing slash if present
                line = line.rstrip('/')

                # Extract the part after the last slash (potential channel name)
                if '/' in line:
                    # Takes the part after the last '/'
                    channel_name = line.rsplit('/', 1)[-1]
                else:
                    # Assume the whole line is the channel name if no slash
                    channel_name = line

                # Basic validation: non-empty, reasonable characters (alphanumeric, underscore)
                # Avoid full URLs mistakenly treated as names
                # Telegram usernames are >= 5 chars, start with letter, contain letters, numbers, underscores
                if channel_name and re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,}$', channel_name):
                    if channel_name not in channels: # Avoid duplicates
                         channels.append(channel_name)
                else:
                    log_callback(f"Skipping invalid or malformed channel entry on line {line_num}: '{original_line.strip()}' -> extracted '{channel_name}'", "WARN")

        log_callback(f"Loaded {len(channels)} unique, valid channel names from {file_path.name}.", "INFO")

        if not channels:
             log_callback("The channel list file is empty or contains no valid channel names.", "ERROR")
             raise ValueError(f"No valid channel names found in {file_path.name}.")

        return channels

    except OSError as e:
        log_callback(f"Error reading channel list file {channellist_file}: {e}", "ERROR")
        raise RuntimeError(f"Error reading channel list file: {e}") from e
    except Exception as e:
        log_callback(f"Unexpected error loading channels from {channellist_file}: {e}", "ERROR")
        raise RuntimeError(f"Unexpected error loading channels: {e}") from e