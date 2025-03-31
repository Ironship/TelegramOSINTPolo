# Main entry point for the Telegram Scraper application.
# import tkinter as tk # OLD
import customtkinter as ctk # NEW
from tkinter import messagebox # Keep messagebox from standard tkinter
import os
import sys
from pathlib import Path # Use pathlib for easier path handling
import tkinter as tk # Potrzebne dla root_err w bloku except


# --- Determine Base Directory ---
# (Keep this section as is)
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
elif __file__:
    base_dir = Path(__file__).parent
else:
    base_dir = Path.cwd()

# --- Dynamically add project root and src to sys.path ---
project_root = base_dir
src_dir = project_root / 'src'
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --- Set CustomTkinter Appearance ---
ctk.set_appearance_mode("System") # Options: "System", "Light", "Dark"
ctk.set_default_color_theme("blue") # Options: "blue", "green", "dark-blue"

# --- Import GUI Component and Dependencies ---
try:
    from gui.main_window import TelegramScraperGUI
    # (Keep other imports and the basic structure of the try/except block)
    from scraper import run_scraping
    from my_telegram_scrapper import SimpleScraperClient
except ImportError as e:
    project_root = base_dir # <-- DODANO TĘ LINIĘ, aby naprawić NameError
    error_details = f"{e}\n\n"
    error_details += f"Could not import required components.\n"
    error_details += f"Please ensure 'src' and 'my_telegram_scrapper' directories exist relative to the executable or script:\n{project_root}\n"
    error_details += "Also, verify that all dependencies (including customtkinter) from requirements.txt are installed."
    print(f"Fatal Error: {error_details}")
    # Attempt to show a GUI error message (using standard tkinter temporarily if ctk fails)
    try:
        # Use a temporary standard Tk root for the error if ctk fails early
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Startup Error", f"Failed to load application components.\n\n{error_details}")
        root_err.destroy()
    except Exception: # Catch broader exceptions here, including tk.TclError
        print("GUI error: Could not display the error message box.")
    sys.exit(1)
except Exception as e:
    # Catch any other unexpected error during initial imports
    print(f"Fatal Error during startup: {e}")
    try:
        # Use a temporary standard Tk root for the error if ctk fails early
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Startup Error", f"An unexpected error occurred during initialization:\n\n{e}")
        root_err.destroy()
    except Exception:
        pass # Console print is the fallback
    sys.exit(1)

# --- Main Execution Function ---
def main():
    """Sets up and runs the CustomTkinter application."""
    # root = tk.Tk() # OLD
    root = ctk.CTk() # NEW
    try:
        # Pass the base_dir (as a string or Path object) to the GUI
        app = TelegramScraperGUI(root, str(base_dir)) # Pass as string if GUI expects it
        root.minsize(600, 700) # Adjusted minsize slightly
        root.mainloop()
    except Exception as e:
        print(f"Fatal Error running the application: {e}")
        # Attempt to show error message if GUI fails during runtime
        try:
             # customtkinter windows might not have winfo_exists in the same way
             # Just try showing the error
             messagebox.showerror("Application Error", f"An unexpected error occurred while running:\n\n{e}")
             if root: # Check if root object exists
                 root.destroy()
        except Exception: # Catch broader exceptions
            pass # Avoid errors if the window is already gone
        sys.exit(1)

# --- Script Entry Point ---
if __name__ == "__main__":
    main()
