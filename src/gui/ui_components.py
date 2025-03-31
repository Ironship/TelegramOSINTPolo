import customtkinter as ctk
from tkinter import ttk
from datetime import date
import os
import webbrowser # Import webbrowser for opening links

# Import config only for CUTOFF_DATE display/limits
from src.config import CUTOFF_DATE

# Standard padding values
PAD_X = 10
PAD_Y = 5
INNER_PAD_X = 5
INNER_PAD_Y = 5

# --- File Selection, Date Pickers, Action Buttons ---
# (Keep create_file_selection_ui, create_specific_date_picker_ui,
#  create_date_range_picker_ui, create_action_buttons_ui as they were
#  in the customtkinter version from the previous steps)
# Example placeholder for one function:
def create_file_selection_ui(master_frame: ctk.CTk, app_instance):
    """Creates the UI section for selecting the channel list file using a dropdown."""
    file_frame = ctk.CTkFrame(master_frame)
    file_frame.pack(padx=PAD_X, pady=(PAD_Y * 2, PAD_Y), fill="x", anchor="n")
    section_label = ctk.CTkLabel(file_frame, text="1. Select Channel List", font=ctk.CTkFont(weight="bold"))
    section_label.pack(anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0))
    app_instance.channel_list_dropdown = ctk.CTkComboBox(
        file_frame, variable=app_instance.channellist_path, state="readonly", width=250
    )
    app_instance.channel_list_dropdown.pack(pady=INNER_PAD_Y, padx=INNER_PAD_X)
    info_label = ctk.CTkLabel( file_frame, text="Select a list. Lists are loaded from 'channelslists' folder.", font=ctk.CTkFont(size=10), text_color="gray")
    info_label.pack(pady=(0, INNER_PAD_Y), padx=INNER_PAD_X)
    return file_frame

# --- (Include the other create_*_ui functions here from previous steps) ---
def create_specific_date_picker_ui(master_frame: ctk.CTk, app_instance):
    # ... (Implementation from previous step) ...
    date_frame = ctk.CTkFrame(master_frame)
    date_frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
    section_label = ctk.CTkLabel(date_frame, text="2a. Download for Specific Date", font=ctk.CTkFont(weight="bold"))
    section_label.pack(anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0))
    date_picker_inner_frame = ctk.CTkFrame(date_frame, fg_color="transparent")
    date_picker_inner_frame.pack(pady=INNER_PAD_Y, fill="x", padx=INNER_PAD_X)
    date_spin_frame = ctk.CTkFrame(date_picker_inner_frame, fg_color="transparent")
    date_spin_frame.pack(side="left", padx=(0, PAD_X))
    current_year = date.today().year; min_year = CUTOFF_DATE.year
    ctk.CTkLabel(date_spin_frame, text="Day:", width=30).pack(side="left", padx=(0, 2))
    app_instance.day_spinbox = ttk.Spinbox(date_spin_frame, from_=1, to=31, textvariable=app_instance.sel_day, width=4, command=lambda: app_instance.validate_date_spinbox('sel'))
    app_instance.day_spinbox.pack(side="left", padx=(0, 8))
    ctk.CTkLabel(date_spin_frame, text="Month:", width=40).pack(side="left", padx=(0, 2))
    app_instance.month_spinbox = ttk.Spinbox( date_spin_frame, from_=1, to=12, textvariable=app_instance.sel_month, width=4, command=lambda: app_instance.validate_date_spinbox('sel'))
    app_instance.month_spinbox.pack(side="left", padx=(0, 8))
    ctk.CTkLabel(date_spin_frame, text="Year:", width=35).pack(side="left", padx=(0, 2))
    app_instance.year_spinbox = ttk.Spinbox( date_spin_frame, from_=min_year, to=current_year, textvariable=app_instance.sel_year, width=6, command=lambda: app_instance.validate_date_spinbox('sel'))
    app_instance.year_spinbox.pack(side="left")
    app_instance.specific_date_button = ctk.CTkButton(date_picker_inner_frame, text="Download This Date", command=lambda: app_instance.start_scraping_base('specific_date'), width=160)
    app_instance.specific_date_button.pack(side="left", padx=(PAD_X, 0))
    return date_frame

def create_date_range_picker_ui(master_frame: ctk.CTk, app_instance):
    # ... (Implementation from previous step) ...
    range_frame = ctk.CTkFrame(master_frame)
    range_frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
    section_label = ctk.CTkLabel(range_frame, text="2b. Download Date Range", font=ctk.CTkFont(weight="bold"))
    section_label.pack(anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0))
    current_year = date.today().year; min_year = CUTOFF_DATE.year; label_width = 70
    start_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
    start_frame.pack(pady=(INNER_PAD_Y, 2), fill="x", padx=INNER_PAD_X)
    ctk.CTkLabel(start_frame, text="Start Date:", width=label_width, anchor='w').pack(side="left", padx=(0, INNER_PAD_X))
    start_spin_frame = ctk.CTkFrame(start_frame, fg_color="transparent")
    start_spin_frame.pack(side="left")
    ctk.CTkLabel(start_spin_frame, text="D:", width=15).pack(side="left", padx=(0, 1))
    app_instance.start_day_spinbox = ttk.Spinbox(start_spin_frame, from_=1, to=31, width=4, textvariable=app_instance.start_day, command=lambda: app_instance.validate_date_spinbox('start'))
    app_instance.start_day_spinbox.pack(side="left", padx=(0, 5))
    ctk.CTkLabel(start_spin_frame, text="M:", width=15).pack(side="left", padx=(0, 1))
    app_instance.start_month_spinbox = ttk.Spinbox(start_spin_frame, from_=1, to=12, width=4, textvariable=app_instance.start_month, command=lambda: app_instance.validate_date_spinbox('start'))
    app_instance.start_month_spinbox.pack(side="left", padx=(0, 5))
    ctk.CTkLabel(start_spin_frame, text="Y:", width=15).pack(side="left", padx=(0, 1))
    app_instance.start_year_spinbox = ttk.Spinbox(start_spin_frame, from_=min_year, to=current_year, width=6, textvariable=app_instance.start_year, command=lambda: app_instance.validate_date_spinbox('start'))
    app_instance.start_year_spinbox.pack(side="left")
    end_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
    end_frame.pack(pady=2, fill="x", padx=INNER_PAD_X)
    ctk.CTkLabel(end_frame, text="End Date:", width=label_width, anchor='w').pack(side="left", padx=(0, INNER_PAD_X))
    end_spin_frame = ctk.CTkFrame(end_frame, fg_color="transparent")
    end_spin_frame.pack(side="left")
    ctk.CTkLabel(end_spin_frame, text="D:", width=15).pack(side="left", padx=(0, 1))
    app_instance.end_day_spinbox = ttk.Spinbox(end_spin_frame, from_=1, to=31, width=4, textvariable=app_instance.end_day, command=lambda: app_instance.validate_date_spinbox('end'))
    app_instance.end_day_spinbox.pack(side="left", padx=(0, 5))
    ctk.CTkLabel(end_spin_frame, text="M:", width=15).pack(side="left", padx=(0, 1))
    app_instance.end_month_spinbox = ttk.Spinbox(end_spin_frame, from_=1, to=12, width=4, textvariable=app_instance.end_month, command=lambda: app_instance.validate_date_spinbox('end'))
    app_instance.end_month_spinbox.pack(side="left", padx=(0, 5))
    ctk.CTkLabel(end_spin_frame, text="Y:", width=15).pack(side="left", padx=(0, 1))
    app_instance.end_year_spinbox = ttk.Spinbox(end_spin_frame, from_=min_year, to=current_year, width=6, textvariable=app_instance.end_year, command=lambda: app_instance.validate_date_spinbox('end'))
    app_instance.end_year_spinbox.pack(side="left")
    button_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
    button_frame.pack(pady=(INNER_PAD_Y * 2, INNER_PAD_Y))
    app_instance.range_date_button = ctk.CTkButton(button_frame, text="Download Date Range", command=lambda: app_instance.start_scraping_base('date_range'), width=180)
    app_instance.range_date_button.pack()
    min_date_str = CUTOFF_DATE.strftime('%Y-%m-%d')
    ctk.CTkLabel(range_frame, text=f"Note: Data is available from {min_date_str} onwards.", text_color="gray").pack(pady=(0, INNER_PAD_Y), anchor='center')
    return range_frame

def create_action_buttons_ui(master_frame: ctk.CTk, app_instance):
    # ... (Implementation from previous step) ...
    actions_frame = ctk.CTkFrame(master_frame)
    actions_frame.pack(padx=PAD_X, pady=PAD_Y, fill="x", anchor="n")
    section_label = ctk.CTkLabel(actions_frame, text="2c. Quick Actions / All / Stop", font=ctk.CTkFont(weight="bold"))
    section_label.pack(anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0))
    button_inner_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
    button_inner_frame.pack(pady=INNER_PAD_Y)
    app_instance.today_button = ctk.CTkButton(button_inner_frame, text="Download Today", command=lambda: app_instance.start_scraping_base('today'), width=150)
    app_instance.today_button.pack(side="left", padx=INNER_PAD_X)
    app_instance.yesterday_button = ctk.CTkButton(button_inner_frame, text="Download Yesterday", command=lambda: app_instance.start_scraping_base('yesterday'), width=150)
    app_instance.yesterday_button.pack(side="left", padx=INNER_PAD_X)
    all_button_text = f"Download All (since {CUTOFF_DATE.year})"
    app_instance.all_button = ctk.CTkButton(button_inner_frame, text=all_button_text, command=lambda: app_instance.start_scraping_base('all'), width=180)
    app_instance.all_button.pack(side="left", padx=INNER_PAD_X)
    app_instance.stop_button = ctk.CTkButton(actions_frame, text="STOP SCRAPING", command=app_instance.stop_scraping, state="disabled", width=200, fg_color="#D32F2F", hover_color="#B71C1C", text_color="white", font=ctk.CTkFont(weight="bold"))
    app_instance.stop_button.pack(pady=(INNER_PAD_Y, INNER_PAD_Y*2))
    ctk.CTkLabel(actions_frame, text="Warning: 'Download All' can take long & create many files!", text_color="#FF8C00").pack(pady=(0,INNER_PAD_Y))
    return actions_frame
# --- End Placeholder ---


def create_log_ui(master_frame: ctk.CTk, app_instance):
    """Creates the scrollable logging text area."""
    log_frame = ctk.CTkFrame(master_frame)
    # Make log frame expand vertically in the main content area
    log_frame.pack(padx=PAD_X, pady=PAD_Y, fill="both", expand=True)

    section_label = ctk.CTkLabel(log_frame, text="Logs", font=ctk.CTkFont(weight="bold"))
    section_label.pack(anchor="w", padx=INNER_PAD_X, pady=(INNER_PAD_Y, 0))

    app_instance.log_text = ctk.CTkTextbox(
        log_frame, wrap="word", height=150, state="disabled"
    )
    app_instance.log_text.pack(fill="both", expand=True, padx=INNER_PAD_X, pady=INNER_PAD_Y)

    # Configure tags (keep as before)
    colors = {"ERROR": "#FF0000", "WARN": "#FFA500", "INFO": "#007ACC", "DEBUG": "#808080"}
    for tag, color in colors.items():
        app_instance.log_text.tag_config(tag, foreground=color)

    # --- REMOVED call to create_analysis_info_ui ---

    return log_frame

# --- NEW/MODIFIED Analysis Info UI for Sidebar ---
def create_analysis_info_ui(master_frame: ctk.CTk, app_instance):
    """Creates the informational section for the sidebar with a clickable link."""
    # The master_frame is now the sidebar frame passed from main_window
    # No need to create another frame inside unless needed for padding/structure
    master_frame.configure(fg_color="transparent") # Make sidebar background transparent if desired

    section_label = ctk.CTkLabel(master_frame, text="3. Data Analysis Tip", font=ctk.CTkFont(weight="bold"))
    section_label.pack(pady=(5, 5), padx=INNER_PAD_X, anchor='w') # Use pack directly into sidebar frame

    # --- Text and Link Handling ---
    # Define parts of the text and the URL
    text_part1 = "After downloading, analyze the 'output_*.txt' files using RAG tools.\nA recommended tool is Google's NotebookLM:"
    url = "https://notebooklm.google.com/"
    text_part2 = "\nUpload the files there to ask questions about the content. Feel free to explore other tools."

    # Set a wrap length appropriate for the sidebar width (adjust if needed)
    sidebar_wrap_length = 180

    # Create label for the text before the link
    label_part1 = ctk.CTkLabel(
        master_frame,
        text=text_part1,
        justify=ctk.LEFT,
        anchor='w',
        wraplength=sidebar_wrap_length
    )
    label_part1.pack(pady=(0, 2), padx=INNER_PAD_X, fill='x')

    # Create the clickable link label
    link_label = ctk.CTkLabel(
        master_frame,
        text=url,
        text_color="cornflowerblue", # Standard link color
        cursor="hand2",             # Change cursor on hover
        justify=ctk.LEFT,
        anchor='w',
        wraplength=sidebar_wrap_length
    )
    link_label.pack(pady=2, padx=INNER_PAD_X, fill='x')
    # Bind left mouse click to open the URL
    link_label.bind("<Button-1>", lambda event: webbrowser.open_new(url))
    # Optional: Add underline
    # link_font = ctk.CTkFont(underline=True)
    # link_label.configure(font=link_font)


    # Create label for the text after the link
    label_part2 = ctk.CTkLabel(
        master_frame,
        text=text_part2,
        justify=ctk.LEFT,
        anchor='w',
        wraplength=sidebar_wrap_length
    )
    label_part2.pack(pady=(2, 5), padx=INNER_PAD_X, fill='x')

    # Return the master_frame (sidebar) itself, although not strictly needed
    return master_frame