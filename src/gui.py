import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import queue
import webbrowser
import os
import re
import calendar
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, Tuple, List

from src.scraper import run_scraping, CUTOFF_DATE

# Padding constants
PAD_X = 10
PAD_Y = 5
INNER_PAD_X = 5
INNER_PAD_Y = 5

# Sentinel values that indicate no real list is selected in the dropdown
_INVALID_LIST_SELECTIONS = ("No lists found", "Error reading lists", "Error scanning lists")


class TelegramScraperGUI:
    """Main GUI class for the Telegram Scraper application."""

    def __init__(self, master: ctk.CTk, base_dir: str):
        self.master = master
        self.base_dir = base_dir
        self.master.title("Telegram Post Downloader")
        self.master.geometry("850x750")

        # Configure root window grid
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=0)
        self.master.grid_rowconfigure(0, weight=1)

        # Variables
        self.channellist_path = ctk.StringVar()
        today = date.today()
        self.sel_year = ctk.IntVar(value=today.year)
        self.sel_month = ctk.IntVar(value=today.month)
        self.sel_day = ctk.IntVar(value=today.day)
        self.start_year = ctk.IntVar(value=today.year)
        self.start_month = ctk.IntVar(value=today.month)
        self.start_day = ctk.IntVar(value=1)
        self.end_year = ctk.IntVar(value=today.year)
        self.end_month = ctk.IntVar(value=today.month)
        self.end_day = ctk.IntVar(value=today.day)

        # Threading and logging
        self.log_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.scraping_thread: Optional[threading.Thread] = None

        # Main content frame (left column)
        self.main_content_frame = ctk.CTkFrame(master, corner_radius=0, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.main_content_frame.grid_rowconfigure(5, weight=1)

        # Sidebar frame (right column)
        self.sidebar_frame = ctk.CTkFrame(master, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ns")
        self.sidebar_frame.grid_propagate(False)

        # Build UI sections
        self._create_file_selection_ui()
        self._create_specific_date_picker_ui()
        self._create_date_range_picker_ui()
        self._create_action_buttons_ui()
        self._create_log_ui()
        self._create_analysis_info_ui()

        # Initialize state
        self._populate_channel_list_dropdown()
        self._process_log_queue()
        self.validate_date_spinbox('sel')
        self.validate_date_spinbox('start')
        self.validate_date_spinbox('end')
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("Application initialized.", "INFO")

    # -------------------------------------------------------------------------
    # UI creation
    # -------------------------------------------------------------------------

    def _create_file_selection_ui(self):
        frame = ctk.CTkFrame(self.main_content_frame)
        frame.pack(padx=PAD_X, pady=(PAD_Y * 2, PAD_Y), fill="x", anchor="n")
        ctk.CTkLabel(frame, text="1. Select Channel List", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0)
        )
        self.channel_list_dropdown = ctk.CTkComboBox(
            frame, variable=self.channellist_path, state="readonly", width=300
        )
        self.channel_list_dropdown.pack(pady=INNER_PAD_Y, padx=INNER_PAD_X)

        # Channel list management buttons
        mgmt_frame = ctk.CTkFrame(frame, fg_color="transparent")
        mgmt_frame.pack(pady=(0, INNER_PAD_Y), padx=INNER_PAD_X)
        self.new_list_button = ctk.CTkButton(
            mgmt_frame, text="New List", command=self._open_new_list_dialog, width=90
        )
        self.new_list_button.pack(side="left", padx=INNER_PAD_X)
        self.edit_list_button = ctk.CTkButton(
            mgmt_frame, text="Edit List", command=self._open_edit_list_dialog, width=90
        )
        self.edit_list_button.pack(side="left", padx=INNER_PAD_X)
        self.delete_list_button = ctk.CTkButton(
            mgmt_frame, text="Delete List", command=self._delete_selected_list,
            fg_color="#D32F2F", hover_color="#B71C1C", width=90
        )
        self.delete_list_button.pack(side="left", padx=INNER_PAD_X)

        ctk.CTkLabel(
            frame,
            text="Lists are loaded from the 'channelslists' folder. Use the buttons above to manage them.",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).pack(pady=(0, INNER_PAD_Y), padx=INNER_PAD_X)

    def _create_specific_date_picker_ui(self):
        frame = ctk.CTkFrame(self.main_content_frame)
        frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
        ctk.CTkLabel(frame, text="2a. Download for Specific Date", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0)
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(pady=INNER_PAD_Y, fill="x", padx=INNER_PAD_X)
        spin_frame = ctk.CTkFrame(inner, fg_color="transparent")
        spin_frame.pack(side="left", padx=(0, PAD_X))
        min_year = CUTOFF_DATE.year
        current_year = date.today().year
        ctk.CTkLabel(spin_frame, text="Day:", width=30).pack(side="left", padx=(0, 2))
        self.day_spinbox = ttk.Spinbox(
            spin_frame, from_=1, to=31, textvariable=self.sel_day, width=4,
            command=lambda: self.validate_date_spinbox('sel')
        )
        self.day_spinbox.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(spin_frame, text="Month:", width=40).pack(side="left", padx=(0, 2))
        self.month_spinbox = ttk.Spinbox(
            spin_frame, from_=1, to=12, textvariable=self.sel_month, width=4,
            command=lambda: self.validate_date_spinbox('sel')
        )
        self.month_spinbox.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(spin_frame, text="Year:", width=35).pack(side="left", padx=(0, 2))
        self.year_spinbox = ttk.Spinbox(
            spin_frame, from_=min_year, to=current_year, textvariable=self.sel_year, width=6,
            command=lambda: self.validate_date_spinbox('sel')
        )
        self.year_spinbox.pack(side="left")
        self.specific_date_button = ctk.CTkButton(
            inner, text="Download This Date",
            command=lambda: self.start_scraping_base('specific_date'), width=160
        )
        self.specific_date_button.pack(side="left", padx=(PAD_X, 0))

    def _create_date_range_picker_ui(self):
        frame = ctk.CTkFrame(self.main_content_frame)
        frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
        ctk.CTkLabel(frame, text="2b. Download Date Range", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0)
        )
        min_year = CUTOFF_DATE.year
        current_year = date.today().year
        label_width = 70

        # Start date row
        start_frame = ctk.CTkFrame(frame, fg_color="transparent")
        start_frame.pack(pady=(INNER_PAD_Y, 2), fill="x", padx=INNER_PAD_X)
        ctk.CTkLabel(start_frame, text="Start Date:", width=label_width, anchor='w').pack(
            side="left", padx=(0, INNER_PAD_X)
        )
        ss = ctk.CTkFrame(start_frame, fg_color="transparent")
        ss.pack(side="left")
        ctk.CTkLabel(ss, text="D:", width=15).pack(side="left", padx=(0, 1))
        self.start_day_spinbox = ttk.Spinbox(
            ss, from_=1, to=31, width=4, textvariable=self.start_day,
            command=lambda: self.validate_date_spinbox('start')
        )
        self.start_day_spinbox.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(ss, text="M:", width=15).pack(side="left", padx=(0, 1))
        self.start_month_spinbox = ttk.Spinbox(
            ss, from_=1, to=12, width=4, textvariable=self.start_month,
            command=lambda: self.validate_date_spinbox('start')
        )
        self.start_month_spinbox.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(ss, text="Y:", width=15).pack(side="left", padx=(0, 1))
        self.start_year_spinbox = ttk.Spinbox(
            ss, from_=min_year, to=current_year, width=6, textvariable=self.start_year,
            command=lambda: self.validate_date_spinbox('start')
        )
        self.start_year_spinbox.pack(side="left")

        # End date row
        end_frame = ctk.CTkFrame(frame, fg_color="transparent")
        end_frame.pack(pady=2, fill="x", padx=INNER_PAD_X)
        ctk.CTkLabel(end_frame, text="End Date:", width=label_width, anchor='w').pack(
            side="left", padx=(0, INNER_PAD_X)
        )
        es = ctk.CTkFrame(end_frame, fg_color="transparent")
        es.pack(side="left")
        ctk.CTkLabel(es, text="D:", width=15).pack(side="left", padx=(0, 1))
        self.end_day_spinbox = ttk.Spinbox(
            es, from_=1, to=31, width=4, textvariable=self.end_day,
            command=lambda: self.validate_date_spinbox('end')
        )
        self.end_day_spinbox.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(es, text="M:", width=15).pack(side="left", padx=(0, 1))
        self.end_month_spinbox = ttk.Spinbox(
            es, from_=1, to=12, width=4, textvariable=self.end_month,
            command=lambda: self.validate_date_spinbox('end')
        )
        self.end_month_spinbox.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(es, text="Y:", width=15).pack(side="left", padx=(0, 1))
        self.end_year_spinbox = ttk.Spinbox(
            es, from_=min_year, to=current_year, width=6, textvariable=self.end_year,
            command=lambda: self.validate_date_spinbox('end')
        )
        self.end_year_spinbox.pack(side="left")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(INNER_PAD_Y * 2, INNER_PAD_Y))
        self.range_date_button = ctk.CTkButton(
            btn_frame, text="Download Date Range",
            command=lambda: self.start_scraping_base('date_range'), width=180
        )
        self.range_date_button.pack()
        ctk.CTkLabel(
            frame,
            text=f"Note: Data is available from {CUTOFF_DATE.strftime('%Y-%m-%d')} onwards.",
            text_color="gray",
        ).pack(pady=(0, INNER_PAD_Y), anchor='center')

    def _create_action_buttons_ui(self):
        frame = ctk.CTkFrame(self.main_content_frame)
        frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
        ctk.CTkLabel(frame, text="2c. Quick Actions / All / Stop", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0)
        )
        btn_inner = ctk.CTkFrame(frame, fg_color="transparent")
        btn_inner.pack(pady=INNER_PAD_Y)
        self.today_button = ctk.CTkButton(
            btn_inner, text="Download Today",
            command=lambda: self.start_scraping_base('today'), width=150
        )
        self.today_button.pack(side="left", padx=INNER_PAD_X)
        self.yesterday_button = ctk.CTkButton(
            btn_inner, text="Download Yesterday",
            command=lambda: self.start_scraping_base('yesterday'), width=150
        )
        self.yesterday_button.pack(side="left", padx=INNER_PAD_X)
        self.all_button = ctk.CTkButton(
            btn_inner, text=f"Download All (since {CUTOFF_DATE.year})",
            command=lambda: self.start_scraping_base('all'), width=180
        )
        self.all_button.pack(side="left", padx=INNER_PAD_X)
        self.stop_button = ctk.CTkButton(
            frame, text="STOP SCRAPING", command=self.stop_scraping,
            state="disabled", width=200, fg_color="#D32F2F", hover_color="#B71C1C",
            text_color="white", font=ctk.CTkFont(weight="bold")
        )
        self.stop_button.pack(pady=(INNER_PAD_Y, INNER_PAD_Y * 2))
        ctk.CTkLabel(
            frame,
            text="Warning: 'Download All' can take long & create many files!",
            text_color="#FF8C00",
        ).pack(pady=(0, INNER_PAD_Y))

    def _create_log_ui(self):
        frame = ctk.CTkFrame(self.main_content_frame)
        frame.pack(padx=PAD_X, pady=PAD_Y, fill="both", expand=True)
        ctk.CTkLabel(frame, text="Logs", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0)
        )
        self.log_text = ctk.CTkTextbox(frame, wrap="word", height=150, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=INNER_PAD_X, pady=INNER_PAD_Y)
        for tag, color in {"ERROR": "#FF0000", "WARN": "#FFA500", "INFO": "#007ACC", "DEBUG": "#808080"}.items():
            self.log_text.tag_config(tag, foreground=color)

    def _create_analysis_info_ui(self):
        self.sidebar_frame.configure(fg_color="transparent")
        ctk.CTkLabel(
            self.sidebar_frame, text="3. Data Analysis Tip", font=ctk.CTkFont(weight="bold")
        ).pack(pady=(5, 5), padx=INNER_PAD_X, anchor='w')
        url = "https://notebooklm.google.com/"
        sidebar_wrap = 180
        ctk.CTkLabel(
            self.sidebar_frame,
            text="After downloading, analyze the 'output_*.txt' files using RAG tools.\n"
                 "A recommended tool is Google's NotebookLM:",
            justify=ctk.LEFT, anchor='w', wraplength=sidebar_wrap,
        ).pack(pady=(0, 2), padx=INNER_PAD_X, fill='x')
        link_label = ctk.CTkLabel(
            self.sidebar_frame, text=url, text_color="cornflowerblue",
            cursor="hand2", justify=ctk.LEFT, anchor='w', wraplength=sidebar_wrap,
        )
        link_label.pack(pady=2, padx=INNER_PAD_X, fill='x')
        link_label.bind("<Button-1>", lambda event: webbrowser.open_new(url))
        ctk.CTkLabel(
            self.sidebar_frame,
            text="\nUpload the files there to ask questions about the content. "
                 "Feel free to explore other tools.",
            justify=ctk.LEFT, anchor='w', wraplength=sidebar_wrap,
        ).pack(pady=(2, 5), padx=INNER_PAD_X, fill='x')

    # -------------------------------------------------------------------------
    # Channel list
    # -------------------------------------------------------------------------

    def _populate_channel_list_dropdown(self):
        channelslists_dir = Path(self.base_dir) / "channelslists"
        default_selection = "No lists found"
        if channelslists_dir.is_dir():
            try:
                channel_files: List[str] = sorted(
                    [f.name for f in channelslists_dir.glob("*.txt") if f.is_file()]
                )
                if channel_files:
                    default_selection = channel_files[0]
                    self.channel_list_dropdown.configure(values=channel_files, state="readonly")
                    self.log_message(f"Found channel lists: {', '.join(channel_files)}", "DEBUG")
                else:
                    self.log_message(f"No .txt files found in {channelslists_dir}", "WARN")
                    self.channel_list_dropdown.configure(values=[default_selection], state="disabled")
            except OSError as e:
                self.log_message(f"Error reading channel list directory: {e}", "ERROR")
                self.channel_list_dropdown.configure(values=["Error reading lists"], state="disabled")
                default_selection = "Error reading lists"
        else:
            self.log_message(f"Channel list directory not found: {channelslists_dir}", "WARN")
            self.channel_list_dropdown.configure(values=[default_selection], state="disabled")
        self.channellist_path.set(default_selection)

    # -------------------------------------------------------------------------
    # Channel list management
    # -------------------------------------------------------------------------

    def _open_new_list_dialog(self):
        """Prompt for a name, then open the editor to create a new channel list."""
        name_dialog = ctk.CTkInputDialog(
            text="Enter a name for the new list (letters, numbers, underscores and hyphens only):",
            title="New Channel List"
        )
        raw_name = name_dialog.get_input()
        if not raw_name:
            return
        raw_name = raw_name.strip()
        if not raw_name:
            return
        if not re.match(r'^[a-zA-Z0-9_-]+$', raw_name):
            messagebox.showerror(
                "Invalid Name",
                "List name can only contain letters, numbers, underscores and hyphens.\n"
                "Example: myNewList or pro_Ukrainian_2024"
            )
            return
        filename = f"{raw_name}.txt"
        filepath = Path(self.base_dir) / "channelslists" / filename
        if filepath.exists():
            messagebox.showwarning("Already Exists", f"A list named '{filename}' already exists.\nEdit it instead.")
            return
        self._open_channel_list_editor(f"New List: {filename}", filename, "", is_new=True)

    def _open_edit_list_dialog(self):
        """Open an editor for the currently selected channel list."""
        selected = self.channellist_path.get().strip()
        if not selected or selected in _INVALID_LIST_SELECTIONS:
            messagebox.showwarning("No List Selected", "Please select a valid channel list to edit.")
            return
        filepath = Path(self.base_dir) / "channelslists" / selected
        try:
            content = filepath.read_text(encoding="utf-8")
        except (IOError, OSError) as e:
            messagebox.showerror("Read Error", f"Could not read list file:\n{e}")
            return
        self._open_channel_list_editor(f"Edit List: {selected}", selected, content)

    def _open_channel_list_editor(self, title: str, filename: str, initial_content: str = "", is_new: bool = False):
        """Open a modal dialog to create or edit a channel list file."""
        channelslists_dir = Path(self.base_dir) / "channelslists"
        filepath = channelslists_dir / filename

        editor = ctk.CTkToplevel(self.master)
        editor.title(title)
        editor.geometry("640x540")
        editor.grab_set()
        editor.focus_set()

        ctk.CTkLabel(
            editor,
            text=(
                "Enter one channel per line – full URL (https://t.me/channel) or channel name only.\n"
                "Lines starting with # are treated as comments and are ignored by the scraper."
            ),
            wraplength=610, justify="left", anchor="w",
        ).pack(pady=(10, 4), padx=12, anchor="w")

        text_box = ctk.CTkTextbox(editor, wrap="word")
        text_box.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        text_box.insert("1.0", initial_content)
        text_box.focus_set()

        def _save():
            content = text_box.get("1.0", "end-1c")
            try:
                channelslists_dir.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content, encoding="utf-8")
                action = "Created" if is_new else "Saved"
                self.log_message(f"{action} channel list: {filename}", "INFO")
                editor.destroy()
                self._populate_channel_list_dropdown()
                self.channellist_path.set(filename)
            except (IOError, OSError, PermissionError) as e:
                messagebox.showerror("Save Error", f"Could not save list file:\n{e}", parent=editor)

        btn_frame = ctk.CTkFrame(editor, fg_color="transparent")
        btn_frame.pack(pady=(4, 10))
        ctk.CTkButton(btn_frame, text="Save", command=_save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=editor.destroy, width=120).pack(side="left", padx=10)

    def _delete_selected_list(self):
        """Delete the currently selected channel list after confirmation."""
        selected = self.channellist_path.get().strip()
        if not selected or selected in _INVALID_LIST_SELECTIONS:
            messagebox.showwarning("No List Selected", "Please select a valid channel list to delete.")
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{selected}'?\nThis cannot be undone."
        ):
            return
        filepath = Path(self.base_dir) / "channelslists" / selected
        try:
            filepath.unlink()
            self.log_message(f"Deleted channel list: {selected}", "INFO")
            self._populate_channel_list_dropdown()
        except (IOError, OSError) as e:
            messagebox.showerror("Delete Error", f"Could not delete list file:\n{e}")

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    def log_message(self, message: str, level: str = "INFO"):
        level = level.upper()
        if level not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            level = "INFO"
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_queue.put(f"[{timestamp}][{level}] {message}")
        except AttributeError:
            print(f"[{timestamp}][{level}] {message}")

    def _process_log_queue(self):
        try:
            while not self.log_queue.empty():
                full_message = self.log_queue.get_nowait()
                tag = next((t for t in ["ERROR", "WARN", "INFO", "DEBUG"] if f"[{t}]" in full_message), "")
                if self.master and hasattr(self, 'log_text') and self.log_text:
                    self.log_text.configure(state="normal")
                    self.log_text.insert(ctk.END, full_message + '\n', (tag,) if tag else ())
                    self.log_text.see(ctk.END)
                    self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing log queue: {e}")
        finally:
            if self.master:
                self.master.after(100, self._process_log_queue)

    # -------------------------------------------------------------------------
    # Date validation
    # -------------------------------------------------------------------------

    def validate_date_spinbox(self, prefix: str):
        try:
            if prefix == 'sel':
                year_var, month_var, day_var, day_spinbox = self.sel_year, self.sel_month, self.sel_day, self.day_spinbox
            elif prefix == 'start':
                year_var, month_var, day_var, day_spinbox = self.start_year, self.start_month, self.start_day, self.start_day_spinbox
            elif prefix == 'end':
                year_var, month_var, day_var, day_spinbox = self.end_year, self.end_month, self.end_day, self.end_day_spinbox
            else:
                return
            month = month_var.get()
            if 1 <= month <= 12:
                _, days_in_month = calendar.monthrange(year_var.get(), month)
                if day_spinbox and getattr(day_spinbox, 'winfo_exists', lambda: False)():
                    day_spinbox.config(to=days_in_month)
                    if day_var.get() > days_in_month:
                        day_var.set(days_in_month)
        except (ValueError, tk.TclError, AttributeError):
            pass
        except Exception as e:
            self.log_message(f"Error validating date spinbox ({prefix}): {e}", "ERROR")

    def _parse_date_or_show_error(self, year_var, month_var, day_var, date_description: str) -> Optional[date]:
        try:
            parsed_date = date(int(year_var.get()), int(month_var.get()), int(day_var.get()))
            if parsed_date > date.today():
                messagebox.showwarning(
                    "Invalid Date",
                    f"The selected {date_description} date ({parsed_date.strftime('%Y-%m-%d')}) cannot be in the future."
                )
                return None
            if parsed_date < CUTOFF_DATE:
                messagebox.showwarning(
                    "Invalid Date",
                    f"The selected {date_description} date ({parsed_date.strftime('%Y-%m-%d')}) must be on or after {CUTOFF_DATE.strftime('%Y-%m-%d')}."
                )
                return None
            return parsed_date
        except ValueError:
            messagebox.showerror("Invalid Date", f"The selected {date_description} date is invalid.")
            return None

    def _get_dates_for_mode(self, mode: str) -> Optional[Tuple[Optional[date], Optional[date], Optional[date]]]:
        target_date_obj = start_date_obj = end_date_obj = None
        if mode == 'today':
            target_date_obj = date.today()
        elif mode == 'yesterday':
            target_date_obj = date.today() - timedelta(days=1)
        elif mode == 'specific_date':
            target_date_obj = self._parse_date_or_show_error(self.sel_year, self.sel_month, self.sel_day, "specific")
            if target_date_obj is None:
                return None
        elif mode == 'date_range':
            start_date_obj = self._parse_date_or_show_error(self.start_year, self.start_month, self.start_day, "start")
            if start_date_obj is None:
                return None
            end_date_obj = self._parse_date_or_show_error(self.end_year, self.end_month, self.end_day, "end")
            if end_date_obj is None:
                return None
            if start_date_obj > end_date_obj:
                messagebox.showwarning("Invalid Date Range", "The 'Start Date' cannot be later than the 'End Date'.")
                return None
        return target_date_obj, start_date_obj, end_date_obj

    # -------------------------------------------------------------------------
    # Scraping control
    # -------------------------------------------------------------------------

    def start_scraping_base(self, mode: str):
        if self.scraping_thread and self.scraping_thread.is_alive():
            messagebox.showwarning("Process Running", "A scraping process is already active.")
            return

        selected_filename = self.channellist_path.get().strip()
        if not selected_filename or selected_filename in _INVALID_LIST_SELECTIONS:
            messagebox.showwarning(
                "Missing Input",
                "Please select a valid channel list from the dropdown.\n"
                "Ensure the 'channelslists' folder exists and contains .txt files."
            )
            return

        channellist_file = str(Path(self.base_dir) / "channelslists" / selected_filename)
        if not os.path.exists(channellist_file):
            messagebox.showerror("File Error", f"The selected channel list file does not exist:\n{channellist_file}")
            return

        date_info = self._get_dates_for_mode(mode)
        if date_info is None:
            return
        target_date_obj, start_date_obj, end_date_obj = date_info

        self.stop_event.clear()
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.configure(state="normal")
            self.log_text.delete('1.0', ctk.END)
            self.log_text.configure(state="disabled")

        self.log_message(f"Initiating scraping process (Mode: '{mode}', List: '{selected_filename}')...", "INFO")
        self._disable_action_buttons()
        self.scraping_thread = threading.Thread(
            target=self._scrape_in_thread,
            args=(channellist_file, mode, target_date_obj, start_date_obj, end_date_obj),
            daemon=True,
        )
        self.scraping_thread.start()

    def stop_scraping(self):
        if self.scraping_thread and self.scraping_thread.is_alive():
            self.log_message("Stop signal sent to scraping thread.", "WARN")
            self.stop_event.set()
            if hasattr(self, 'stop_button') and self.stop_button:
                self.stop_button.configure(state="disabled")
        else:
            self.log_message("No active scraping process to stop.", "INFO")

    def _scrape_in_thread(self, channellist_file, mode, target_date, start_date, end_date):
        output_files = []
        error_occurred = False
        final_message = "An unknown error occurred."
        final_message_type = "ERROR"
        try:
            output_files = run_scraping(
                channellist_file=channellist_file,
                mode=mode,
                target_date=target_date,
                start_date=start_date,
                end_date=end_date,
                log_callback=self.log_message,
                stop_event=self.stop_event,
                base_dir=self.base_dir,
            )
            if self.stop_event.is_set():
                final_message = "Scraping process was interrupted by the user."
                final_message_type = "WARN"
            elif not output_files:
                final_date_to_show = target_date if mode != 'date_range' else end_date
                start_date_for_msg = start_date if mode == 'date_range' else None
                final_message = self._generate_no_posts_message(mode, final_date_to_show, start_date_for_msg)
                final_message_type = "INFO"
            else:
                files_str = "\n".join([os.path.basename(f) for f in output_files])
                final_message = f"Scraping completed successfully.\nCreated/updated files:\n{files_str}"
                final_message_type = "SUCCESS"
        except (FileNotFoundError, ValueError, RuntimeError, NameError) as e:
            error_occurred = True
            final_message = f"Scraping failed: {e}"
        except Exception as e:
            error_occurred = True
            final_message = f"An unexpected critical error occurred: {type(e).__name__} - {e}"
            self.log_message(final_message, "ERROR")
        finally:
            if self.master:
                self.master.after(0, self._show_final_message, final_message, final_message_type, error_occurred)
                self.master.after(0, self._reset_buttons)

    def _generate_no_posts_message(self, mode: str, target_date: Optional[date], start_date: Optional[date]) -> str:
        date_info = ""
        cutoff_str = f" (after {CUTOFF_DATE.strftime('%Y-%m-%d')})"
        if mode == 'date_range' and start_date and target_date:
            date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {target_date.strftime('%Y-%m-%d')}"
        elif target_date and mode != 'all':
            date_info = f" for {target_date.strftime('%Y-%m-%d')}"
        elif mode == 'all':
            date_info = " in 'all' mode"
        return f"No posts matching the criteria were found{date_info}{cutoff_str}."

    def _show_final_message(self, message: str, message_type: str, error_occurred: bool):
        try:
            if self.master:
                if message_type == "SUCCESS":
                    messagebox.showinfo("Success!", message)
                elif message_type == "INFO":
                    messagebox.showinfo("No Results", message)
                elif message_type == "WARN":
                    messagebox.showwarning("Interrupted", message)
                else:
                    messagebox.showerror("Error", f"{message}\n\nPlease check the logs for more details.")
        except tk.TclError:
            pass

    # -------------------------------------------------------------------------
    # Button state management
    # -------------------------------------------------------------------------

    def _set_widget_state(self, widget_name: str, state: str):
        widget = getattr(self, widget_name, None)
        if isinstance(widget, ctk.CTkButton):
            try:
                widget.configure(state=state)
            except Exception:
                pass
        elif isinstance(widget, ttk.Spinbox):
            if widget and getattr(widget, 'winfo_exists', lambda: False)():
                try:
                    widget.config(state=tk.NORMAL if state == "normal" else tk.DISABLED)
                except (tk.TclError, AttributeError):
                    pass

    def _disable_action_buttons(self):
        for name in [
            'specific_date_button', 'range_date_button', 'today_button', 'yesterday_button', 'all_button',
            'channel_list_dropdown', 'new_list_button', 'edit_list_button', 'delete_list_button',
            'day_spinbox', 'month_spinbox', 'year_spinbox',
            'start_day_spinbox', 'start_month_spinbox', 'start_year_spinbox',
            'end_day_spinbox', 'end_month_spinbox', 'end_year_spinbox',
        ]:
            self._set_widget_state(name, "disabled")
        self._set_widget_state('stop_button', "normal")

    def _reset_buttons(self):
        for name in [
            'specific_date_button', 'range_date_button', 'today_button', 'yesterday_button', 'all_button',
            'channel_list_dropdown', 'new_list_button', 'edit_list_button', 'delete_list_button',
            'day_spinbox', 'month_spinbox', 'year_spinbox',
            'start_day_spinbox', 'start_month_spinbox', 'start_year_spinbox',
            'end_day_spinbox', 'end_month_spinbox', 'end_year_spinbox',
        ]:
            self._set_widget_state(name, "normal")
        self._set_widget_state('stop_button', "disabled")

    # -------------------------------------------------------------------------
    # Window close
    # -------------------------------------------------------------------------

    def on_closing(self):
        if self.scraping_thread and self.scraping_thread.is_alive():
            if messagebox.askyesno(
                "Confirm Exit",
                "Scraping is still in progress.\nDo you want to stop the process and exit?"
            ):
                self.log_message("Exit requested during active scraping. Sending stop signal...", "WARN")
                self.stop_event.set()
                self.master.after(200, self.master.destroy)
        else:
            self.log_message("Application closing.", "INFO")
            if self.master:
                self.master.destroy()
