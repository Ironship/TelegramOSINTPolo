# import tkinter as tk # OLD
import customtkinter as ctk # NEW
import tkinter as tk # Keep standard tk for messagebox, TclError, maybe Spinbox type check
from tkinter import filedialog, messagebox, ttk # Keep ttk for Spinbox type check
import threading
import queue
from datetime import date, timedelta, datetime
import calendar
import os
from pathlib import Path
from typing import Optional, Callable, Tuple, Any # Added Any

from src.config import CUTOFF_DATE
try:
    from src.scraper import run_scraping
except ImportError:
    messagebox.showerror("Import Error", "Could not load the core scraping module ('src.scraper'). Please check installation.")
    import sys
    sys.exit(1)

class GuiEventHandlers:
    """Contains event handling methods for the TelegramScraperGUI."""

    def __init__(self, app_instance):
        self.app = app_instance

    # --- Log Handling ---
    def log_message(self, message: str, level: str = "INFO"):
        # (Keep this method as is)
        level = level.upper()
        if level not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            level = "INFO"
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}][{level}] {message}"
        try:
             self.app.log_queue.put(formatted_message)
        except AttributeError:
             print(f"Fallback Log: {formatted_message}")

    def process_log_queue(self):
        """Processes messages from the log queue and updates the GUI log text (CTkTextbox)."""
        try:
            while not self.app.log_queue.empty():
                full_message = self.app.log_queue.get_nowait()
                tag = ""
                # Determine tag based on level prefix (same logic)
                if "[ERROR]" in full_message: tag = "ERROR"
                elif "[WARN]" in full_message: tag = "WARN"
                elif "[INFO]" in full_message: tag = "INFO"
                elif "[DEBUG]" in full_message: tag = "DEBUG"

                # Check if master window and log_text widget exist
                # Use ctk checks if available, otherwise standard tkinter checks
                if self.app.master and hasattr(self.app, 'log_text') and self.app.log_text:
                    # CTkTextbox needs state change to insert
                    self.app.log_text.configure(state="normal")
                    if tag:
                        self.app.log_text.insert(ctk.END, full_message + '\n', (tag,))
                    else:
                        self.app.log_text.insert(ctk.END, full_message + '\n')
                    self.app.log_text.see(ctk.END) # Scroll to the end
                    self.app.log_text.configure(state="disabled") # Disable editing again
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing log queue: {e}") # Fallback print
        finally:
            # Reschedule check only if the master window still exists (basic check)
            if self.app.master:
                self.app.master.after(100, self.process_log_queue)


    # --- File Dialog (No longer used for channel list) ---
    def open_file_dialog(self):
        """Opens a dialog to select the channel list file. (DEPRECATED)"""
        self.log_message("Browse button clicked (feature deprecated, use dropdown).", "WARN")
        messagebox.showinfo("Info", "Channel list selection is now done via the dropdown menu.")
        # Keep original logic commented out or remove if preferred
        # initial_dir_path = Path(self.app.base_dir) / "channelslists"
        # if not initial_dir_path.is_dir():
        #      initial_dir_path = Path(self.app.base_dir)
        # filename = filedialog.askopenfilename(...)
        # if filename: self.app.channellist_path.set(filename) ...


    # --- Date Validation ---
    def validate_date_spinbox(self, prefix: str):
        """Adjusts the maximum day for the selected month and year spinboxes."""
        # (This logic interacts with tk.IntVar and ttk.Spinbox, should remain compatible)
        try:
            if prefix == 'sel':
                year_var, month_var, day_var = self.app.sel_year, self.app.sel_month, self.app.sel_day
                day_spinbox = self.app.day_spinbox
            elif prefix == 'start':
                year_var, month_var, day_var = self.app.start_year, self.app.start_month, self.app.start_day
                day_spinbox = self.app.start_day_spinbox
            elif prefix == 'end':
                year_var, month_var, day_var = self.app.end_year, self.app.end_month, self.app.end_day
                day_spinbox = self.app.end_day_spinbox
            else:
                self.log_message(f"Invalid prefix '{prefix}' for date validation.", "WARN")
                return

            year = year_var.get()
            month = month_var.get()

            if 1 <= month <= 12:
                _, days_in_month = calendar.monthrange(year, month)
                # Configure spinbox only if it exists (using standard tkinter methods)
                if day_spinbox and getattr(day_spinbox, 'winfo_exists', lambda: False)(): # Safer check
                     day_spinbox.config(to=days_in_month)
                     if day_var.get() > days_in_month:
                         day_var.set(days_in_month)
        except ValueError: pass
        except (tk.TclError, AttributeError): pass
        except Exception as e:
            self.log_message(f"Error validating date spinbox ({prefix}): {e}", "ERROR")

    # --- Date Parsing Helpers ---
    def _parse_date_or_show_error(self, year_var, month_var, day_var, date_description: str) -> Optional[date]:
        # (This logic uses tk.IntVar.get(), should remain compatible)
        # (Keep this method as is)
        try:
            year_val, month_val, day_val = year_var.get(), month_var.get(), day_var.get()
            # Explicitly convert to integers
            parsed_date = date(int(year_val), int(month_val), int(day_val))
            if parsed_date > date.today():
                 messagebox.showwarning("Invalid Date", f"The selected {date_description} date ({parsed_date.strftime('%Y-%m-%d')}) cannot be in the future.")
                 return None
            if parsed_date < CUTOFF_DATE:
                 messagebox.showwarning("Invalid Date", f"The selected {date_description} date ({parsed_date.strftime('%Y-%m-%d')}) must be on or after {CUTOFF_DATE.strftime('%Y-%m-%d')}.")
                 return None
            return parsed_date
        except ValueError:
             messagebox.showerror("Invalid Date", f"The selected {date_description} date is invalid. Please check the year, month, and day.")
             return None

    def _get_dates_for_mode(self, mode: str) -> Optional[Tuple[Optional[date], Optional[date], Optional[date]]]:
         # (This logic uses _parse_date_or_show_error, keep as is)
         target_date_obj: Optional[date] = None
         start_date_obj: Optional[date] = None
         end_date_obj: Optional[date] = None

         if mode == 'today': target_date_obj = date.today()
         elif mode == 'yesterday': target_date_obj = date.today() - timedelta(days=1)
         elif mode == 'specific_date':
             target_date_obj = self._parse_date_or_show_error(self.app.sel_year, self.app.sel_month, self.app.sel_day, "specific")
             if target_date_obj is None: return None
         elif mode == 'date_range':
             start_date_obj = self._parse_date_or_show_error(self.app.start_year, self.app.start_month, self.app.start_day, "start")
             if start_date_obj is None: return None
             end_date_obj = self._parse_date_or_show_error(self.app.end_year, self.app.end_month, self.app.end_day, "end")
             if end_date_obj is None: return None
             if start_date_obj > end_date_obj:
                 messagebox.showwarning("Invalid Date Range", "The 'Start Date' cannot be later than the 'End Date'.")
                 return None
         elif mode == 'all': pass
         return target_date_obj, start_date_obj, end_date_obj


    # --- Scraping Control ---
    def start_scraping_base(self, mode: str):
        """Base function to validate inputs and initiate scraping for any mode."""
        if self.app.scraping_thread and self.app.scraping_thread.is_alive():
            messagebox.showwarning("Process Running", "A scraping process is already active.")
            return

        # === NEW: Validate Channel List File from Dropdown ===
        selected_filename = self.app.channellist_path.get().strip()
        if not selected_filename or selected_filename in ["No lists found", "Error reading lists", "Error scanning lists"]:
            messagebox.showwarning("Missing Input", "Please select a valid channel list from the dropdown.\nEnsure the 'channelslists' folder exists and contains .txt files.")
            return

        # Construct the full path
        channelslists_dir = Path(self.app.base_dir) / "channelslists"
        channellist_file = str(channelslists_dir / selected_filename) # Convert Path to string for os.path.exists

        if not os.path.exists(channellist_file): # Check full path existence
            messagebox.showerror("File Error", f"The selected channel list file does not seem to exist:\n{channellist_file}")
            # Consider re-populating the dropdown here if the file vanished
            # self.app._populate_channel_list_dropdown()
            return
        # === END NEW ===

        # Get and Validate Dates (No changes needed here)
        date_info = self._get_dates_for_mode(mode)
        if date_info is None: return
        target_date_obj, start_date_obj, end_date_obj = date_info

        # --- Start Scraping Thread ---
        self.app.stop_event.clear()

        # Clear log area (using CTkTextbox configure)
        if hasattr(self.app, 'log_text') and self.app.log_text:
            self.app.log_text.configure(state="normal")
            self.app.log_text.delete('1.0', ctk.END)
            self.app.log_text.configure(state="disabled")

        self.log_message(f"Initiating scraping process (Mode: '{mode}', List: '{selected_filename}')...", "INFO")
        self.disable_action_buttons()

        self.app.scraping_thread = threading.Thread(
            target=self.scrape_in_thread,
            # Pass the FULL PATH to the scrape function
            args=(channellist_file, mode, target_date_obj, start_date_obj, end_date_obj),
            daemon=True
        )
        self.app.scraping_thread.start()

    def stop_scraping(self):
        # (Keep this method as is, stop_event is independent of UI lib)
        if self.app.scraping_thread and self.app.scraping_thread.is_alive():
            self.log_message("Stop signal sent to scraping thread.", "WARN")
            self.app.stop_event.set()
            if hasattr(self.app, 'stop_button') and self.app.stop_button:
                 self.app.stop_button.configure(state="disabled") # Use configure for ctk
        else:
            self.log_message("No active scraping process to stop.", "INFO")

    def scrape_in_thread(self, channellist_file, mode, target_date, start_date, end_date):
        # (Keep this method's core logic - it calls run_scraping)
        # (run_scraping is UI independent, just uses callbacks)
        output_files = []
        error_occurred = False
        final_message = "An unknown error occurred."
        final_message_type = "ERROR"

        try:
            output_files = run_scraping(
                channellist_file=channellist_file, # Pass the full path
                mode=mode,
                target_date=target_date,
                start_date=start_date,
                end_date=end_date,
                log_callback=self.log_message,
                stop_event=self.app.stop_event,
                base_dir=self.app.base_dir
            )

            if self.app.stop_event.is_set():
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

        except ImportError as e:
             error_occurred = True
             final_message = f"Import Error: {e}\nCannot run scraping. Check installation and file structure."
             self.log_message(final_message, "ERROR")
        except (FileNotFoundError, ValueError, RuntimeError, NameError) as e:
             error_occurred = True
             final_message = f"Scraping failed: {e}"
        except Exception as e:
             error_occurred = True
             final_message = f"An unexpected critical error occurred: {type(e).__name__} - {e}"
             self.log_message(final_message, "ERROR")

        finally:
            # --- Schedule GUI updates back on the main thread ---
            if self.app.master: # Basic check if master exists
                 self.app.master.after(0, self.show_final_message, final_message, final_message_type, error_occurred)
                 self.app.master.after(0, self.reset_buttons)

    def _generate_no_posts_message(self, mode: str, target_date: Optional[date], start_date: Optional[date]) -> str:
         # (Keep this method as is)
         date_info = ""
         cutoff_str = f" (after {CUTOFF_DATE.strftime('%Y-%m-%d')})"
         if mode == 'date_range' and start_date and target_date: date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {target_date.strftime('%Y-%m-%d')}"
         elif target_date and mode != 'all': date_info = f" for {target_date.strftime('%Y-%m-%d')}"
         elif mode == 'all': date_info = " in 'all' mode"
         return f"No posts matching the criteria were found{date_info}{cutoff_str}."

    # --- GUI Message Functions (run in main thread via master.after) ---
    def show_final_message(self, message: str, message_type: str, error_occurred: bool):
        # (Keep this method as is, uses standard messagebox)
        try:
            if self.app.master:
                if message_type == "SUCCESS": messagebox.showinfo("Success!", message)
                elif message_type == "INFO": messagebox.showinfo("No Results", message)
                elif message_type == "WARN": messagebox.showwarning("Interrupted", message)
                else: # ERROR
                     full_error_msg = f"{message}\n\nPlease check the logs for more details."
                     messagebox.showerror("Error", full_error_msg)
        except tk.TclError: pass # Window might have been closed

    # --- Button State Management ---
    def _set_button_state(self, button_name: str, state: str): # Use string state for ctk
        """Safely sets the state of a button widget attribute on the app instance."""
        button_widget = getattr(self.app, button_name, None)
        # Check for CTkButton, fallback to tk.Button/ttk.Button might be needed if mixing
        # Also check if Spinboxes are controlled here - they use standard tk state
        if isinstance(button_widget, (ctk.CTkButton)):
             # Check if widget is destroyed - basic check if object exists
             if button_widget:
                 try:
                     button_widget.configure(state=state) # Use configure for ctk
                 except Exception as e: # Catch broad exceptions
                     self.log_message(f"Could not configure button '{button_name}': {e}", "WARN")
                     pass
        elif isinstance(button_widget, (ttk.Spinbox)): # Handle spinboxes if needed
            if button_widget and getattr(button_widget, 'winfo_exists', lambda: False)():
                 try:
                    # Spinbox uses standard tk state constants
                    tk_state = tk.NORMAL if state == "normal" else tk.DISABLED
                    button_widget.config(state=tk_state)
                 except (tk.TclError, AttributeError): pass


    def disable_action_buttons(self):
        """Disables all action buttons and enables the stop button."""
        if not self.app.master: return
        buttons_to_disable = [
            'specific_date_button', 'range_date_button', 'today_button',
            'yesterday_button', 'all_button',
            'channel_list_dropdown' # Disable dropdown during run
            # 'browse_button' # Removed
        ]
        # Also disable spinboxes
        spinboxes_to_disable = [
            'day_spinbox', 'month_spinbox', 'year_spinbox',
            'start_day_spinbox', 'start_month_spinbox', 'start_year_spinbox',
            'end_day_spinbox', 'end_month_spinbox', 'end_year_spinbox'
        ]
        for btn_name in buttons_to_disable + spinboxes_to_disable:
             self._set_button_state(btn_name, "disabled") # Use string state "disabled"
        self._set_button_state('stop_button', "normal") # Use string state "normal"

    def reset_buttons(self):
        """Resets button states after scraping finishes or is stopped."""
        if not self.app.master: return
        buttons_to_enable = [
            'specific_date_button', 'range_date_button', 'today_button',
            'yesterday_button', 'all_button',
            'channel_list_dropdown' # Re-enable dropdown
            # 'browse_button' # Removed
        ]
        # Also enable spinboxes
        spinboxes_to_enable = [
            'day_spinbox', 'month_spinbox', 'year_spinbox',
            'start_day_spinbox', 'start_month_spinbox', 'start_year_spinbox',
            'end_day_spinbox', 'end_month_spinbox', 'end_year_spinbox'
        ]
        for btn_name in buttons_to_enable + spinboxes_to_enable:
             self._set_button_state(btn_name, "normal")
        self._set_button_state('stop_button', "disabled")


    # --- Window Closing Handler ---
    def on_closing(self):
        # (Keep logic, check master existence simply)
        if self.app.scraping_thread and self.app.scraping_thread.is_alive():
            if messagebox.askyesno("Confirm Exit", "Scraping is still in progress.\nDo you want to stop the process and exit?"):
                self.log_message("Exit requested during active scraping. Sending stop signal...", "WARN")
                self.app.stop_event.set()
                # Use destroy directly after a short delay
                self.app.master.after(200, self.app.master.destroy)
            else:
                return # Do not close
        else:
            self.log_message("Application closing.", "INFO")
            if self.app.master: # Check before destroying
                self.app.master.destroy()