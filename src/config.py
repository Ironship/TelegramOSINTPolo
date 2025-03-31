# TelegramOSINTPolo-main/src/config.py
from datetime import date

# --- CONSTANTS ---
ARCHIVE_DIR_NAME: str = "archive"

# Stop scraping posts older than this date (inclusive)
# Ensures we don't go back indefinitely.
CUTOFF_DATE: date = date(2022, 1, 1)

# Potentially add other configurations here if needed
# DEFAULT_OUTPUT_FILENAME_FORMAT: str = "output_{list_name}_{date}.txt"
# LOG_LEVEL: str = "INFO"