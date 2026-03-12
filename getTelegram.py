import customtkinter as ctk
from tkinter import messagebox
import sys
import tkinter as tk
from pathlib import Path


# --- Determine Base Directory ---
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
elif __file__:
    base_dir = Path(__file__).parent
else:
    base_dir = Path.cwd()

# --- Add project root and src to sys.path ---
project_root = base_dir
src_dir = project_root / 'src'
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --- Set CustomTkinter Appearance ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- Import GUI ---
try:
    from src.gui import TelegramScraperGUI
except ImportError as e:
    error_details = (
        f"{e}\n\nCould not import required components.\n"
        f"Please ensure 'src' and 'my_telegram_scrapper' directories exist relative to:\n{project_root}\n"
        "Also, verify that all dependencies from requirements.txt are installed."
    )
    print(f"Fatal Error: {error_details}")
    try:
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Startup Error", f"Failed to load application components.\n\n{error_details}")
        root_err.destroy()
    except Exception:
        print("GUI error: Could not display the error message box.")
    sys.exit(1)
except Exception as e:
    print(f"Fatal Error during startup: {e}")
    try:
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Startup Error", f"An unexpected error occurred during initialization:\n\n{e}")
        root_err.destroy()
    except Exception:
        pass
    sys.exit(1)


def main():
    """Sets up and runs the CustomTkinter application."""
    root = ctk.CTk()
    try:
        TelegramScraperGUI(root, str(base_dir))
        root.minsize(600, 700)
        root.mainloop()
    except Exception as e:
        print(f"Fatal Error running the application: {e}")
        try:
            messagebox.showerror("Application Error", f"An unexpected error occurred while running:\n\n{e}")
            if root:
                root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
