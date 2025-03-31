import customtkinter as ctk
from tkinter import messagebox
import queue
import threading
from datetime import date
from typing import Optional, List
from pathlib import Path
import os

# Import UI component creation functions and event handlers
from .ui_components import (
    create_file_selection_ui,
    create_specific_date_picker_ui,
    create_date_range_picker_ui,
    create_action_buttons_ui,
    create_log_ui,
    # Import the analysis info UI function separately
    create_analysis_info_ui
)
from .event_handlers import GuiEventHandlers
from src.config import CUTOFF_DATE # Ensure CUTOFF_DATE is imported if used here, though likely not directly

class TelegramScraperGUI:
    """
    Main class for the Telegram Scraper GUI application using CustomTkinter.
    Orchestrates UI setup and event handling with a grid layout.
    """
    def __init__(self, master: ctk.CTk, base_dir: str):
        """
        Initializes the main GUI window.

        Args:
            master: The root CustomTkinter window (ctk.CTk instance).
            base_dir: The base directory path (string) for file operations.
        """
        self.master: ctk.CTk = master
        self.base_dir: str = base_dir
        self.master.title("Telegram Post Downloader v3.2 (Grid Layout)") # Updated version/title
        self.master.geometry("850x750") # Adjusted size for sidebar

        # --- Configure root window's grid ---
        # Column 0 (main content) will expand, Column 1 (sidebar) fixed width
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=0) # Sidebar doesn't expand horizontally
        # Row 0 will contain everything and expand vertically
        self.master.grid_rowconfigure(0, weight=1)

        # --- CustomTkinter Variables ---
        self.channellist_path = ctk.StringVar() # Will store the selected *filename*

        # Date Picker Variables (initialize with today's date)
        today = date.today()
        self.sel_year = ctk.IntVar(value=today.year)
        self.sel_month = ctk.IntVar(value=today.month)
        self.sel_day = ctk.IntVar(value=today.day)
        self.start_year = ctk.IntVar(value=today.year)
        self.start_month = ctk.IntVar(value=today.month)
        self.start_day = ctk.IntVar(value=1) # Default start day to 1st
        self.end_year = ctk.IntVar(value=today.year)
        self.end_month = ctk.IntVar(value=today.month)
        self.end_day = ctk.IntVar(value=today.day) # Default end day to today

        # --- Threading and Logging ---
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.scraping_thread: Optional[threading.Thread] = None

        # --- Initialize Event Handlers ---
        self.handlers = GuiEventHandlers(self)

        # --- Create Main Frames using grid ---
        # Main content frame on the left
        self.main_content_frame = ctk.CTkFrame(master, corner_radius=0, fg_color="transparent")
        # Place in grid cell (0,0), make it stick to all sides (nsew)
        self.main_content_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        # Configure internal row for log frame (assuming 5 main widgets packed above it)
        self.main_content_frame.grid_rowconfigure(5, weight=1) # Allow log frame (index 5 if 5 packed above) to expand

        # Sidebar frame on the right
        self.sidebar_frame = ctk.CTkFrame(master, width=200, corner_radius=0) # Keep defined width
         # Place in grid cell (0,1), make it stick vertically (ns)
        self.sidebar_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ns")
        # Prevent sidebar from shrinking to content
        self.sidebar_frame.grid_propagate(False)


        # --- Create UI Sections (using pack inside their respective frames) ---
        # Widgets packed into main_content_frame
        create_file_selection_ui(self.main_content_frame, self)
        create_specific_date_picker_ui(self.main_content_frame, self)
        create_date_range_picker_ui(self.main_content_frame, self)
        create_action_buttons_ui(self.main_content_frame, self)
        create_log_ui(self.main_content_frame, self) # This creates self.log_text

        # Widgets packed into sidebar_frame
        create_analysis_info_ui(self.sidebar_frame, self)

        # --- Populate Channel List Dropdown ---
        self._populate_channel_list_dropdown()

        # --- Initialize and Start Log Processing Loop ---
        self.process_log_queue()

        # --- Initial Validation for Date Pickers ---
        self.validate_date_spinbox('sel')
        self.validate_date_spinbox('start')
        self.validate_date_spinbox('end')

        # --- Window Close Protocol ---
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Log application start
        self.log_message("Application initialized with grid layout.", "INFO")

    def _populate_channel_list_dropdown(self):
        """Finds .txt files in 'channelslists' and populates the dropdown."""
        channelslists_dir = Path(self.base_dir) / "channelslists"
        channel_files: List[str] = []
        default_selection = "No lists found"

        # Ensure dropdown widget exists before trying to configure it
        if not hasattr(self, 'channel_list_dropdown') or not self.channel_list_dropdown:
            self.log_message("Channel list dropdown widget not yet created.", "ERROR")
            self.channellist_path.set(default_selection) # Set variable anyway
            return

        if channelslists_dir.is_dir():
            try:
                # Get only filenames, filter for .txt, sort alphabetically
                channel_files = sorted([
                    f.name for f in channelslists_dir.glob("*.txt") if f.is_file()
                ])
                if channel_files:
                    default_selection = channel_files[0] # Default to the first file found
                    # Configure the dropdown
                    self.channel_list_dropdown.configure(values=channel_files, state="readonly") # Use readonly state
                    self.log_message(f"Found channel lists: {', '.join(channel_files)}", "DEBUG")
                else:
                    self.log_message(f"No .txt files found in {channelslists_dir}", "WARN")
                    self.channel_list_dropdown.configure(values=[default_selection], state="disabled")

            except OSError as e:
                self.log_message(f"Error reading channel list directory {channelslists_dir}: {e}", "ERROR")
                self.channel_list_dropdown.configure(values=[f"Error reading lists"], state="disabled")
                default_selection = "Error reading lists"
            except Exception as e:
                self.log_message(f"Unexpected error scanning for channel lists: {e}", "ERROR")
                self.channel_list_dropdown.configure(values=[f"Error scanning lists"], state="disabled")
                default_selection = "Error scanning lists"
        else:
            self.log_message(f"Channel list directory not found: {channelslists_dir}", "WARN")
            self.channel_list_dropdown.configure(values=[default_selection], state="disabled")

        # Set the variable for the dropdown
        self.channellist_path.set(default_selection)


    # --- Method Delegation to Handlers ---
    # These methods provide a clean interface and delegate the actual work
    # to the GuiEventHandlers instance.

    def open_file_dialog(self): # Deprecated method
        self.handlers.open_file_dialog()

    def validate_date_spinbox(self, prefix: str):
        self.handlers.validate_date_spinbox(prefix)

    def log_message(self, message: str, level: str = "INFO"):
        """Logs a message via the handler (which queues it)."""
        self.handlers.log_message(message, level)

    def process_log_queue(self):
        """Starts or continues processing the log queue via the handler."""
        self.handlers.process_log_queue()

    def start_scraping_base(self, mode: str):
        """Initiates scraping via the handler."""
        self.handlers.start_scraping_base(mode)

    def stop_scraping(self):
        """Stops scraping via the handler."""
        self.handlers.stop_scraping()

    def disable_action_buttons(self):
        """Disables buttons during scraping via the handler."""
        self.handlers.disable_action_buttons()

    def reset_buttons(self):
        """Resets button states via the handler."""
        self.handlers.reset_buttons()

    def on_closing(self):
        """Handles window closing via the handler."""
        self.handlers.on_closing()

# Note: The actual Tkinter mainloop is called in getTelegram.py, not here.