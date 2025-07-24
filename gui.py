import tkinter as tk
from tkinter import ttk, filedialog
import os
from config import save_config, load_config

# Available options for scheduled sync intervals
SCHEDULE_OPTIONS = [
    "Never",
    "Every 15 min",
    "Every 30 min",
    "Hourly",
    "Daily @ 02:00"
]

# Tracks current profile name (e.g. "default", "travel")
profile_name = "default"
config_data = {}

# Opens folder selection dialog and updates corresponding config field
def choose_folder(label_key, entry_widget):
    folder = filedialog.askdirectory()
    if folder:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, folder)
        config_data[label_key] = folder

# Toggles Watchdog mode and saves the user's selection to config
def toggle_watchdog_checkbox():
    config_data["use_watchdog"] = watchdog_var.get()

# Handles change in schedule dropdown and updates config
def change_schedule_interval(event):
    selected = schedule_var.get()
    config_data["schedule_interval"] = selected

# Builds and launches the config GUI window
def launch_gui(save_callback, autostart_callback, is_dev=False, profile="default"):
    global config_data, profile_name
    profile_name = profile
    config_data = load_config(profile_name) or {}

    root = tk.Tk()
    root.title("PlaylistConverter Setup")
    root.geometry("480x520")
    root.resizable(False, False)

    tk.Label(root, text="🎧 PC Playlist Folder:").pack(pady=(20, 0))
    pc_entry = tk.Entry(root, width=50)
    pc_entry.pack()
    pc_entry.insert(0, config_data.get("pc_folder", ""))
    tk.Button(root, text="Browse...", command=lambda: choose_folder("pc_folder", pc_entry)).pack(pady=(2, 10))

    tk.Label(root, text="📱 Smartphone Playlist Folder:").pack()
    phone_entry = tk.Entry(root, width=50)
    phone_entry.pack()
    phone_entry.insert(0, config_data.get("smartphone_folder", ""))
    tk.Button(root, text="Browse...", command=lambda: choose_folder("smartphone_folder", phone_entry)).pack(pady=(2, 10))

    # Watchdog sync checkbox
    global watchdog_var
    watchdog_var = tk.BooleanVar()
    watchdog_var.set(config_data.get("use_watchdog", True))
    tk.Checkbutton(root, text="Enable Real-Time Sync (Watchdog)", variable=watchdog_var,
                   command=toggle_watchdog_checkbox).pack(pady=(10, 0))

    # Sync interval dropdown
    global schedule_var
    schedule_var = tk.StringVar()
    current_schedule = config_data.get("schedule_interval", "Never")
    if current_schedule not in SCHEDULE_OPTIONS:
        current_schedule = "Never"
    schedule_var.set(current_schedule)
    tk.Label(root, text="⏱️ Scheduled Sync Interval:").pack(pady=(15, 0))
    schedule_dropdown = ttk.Combobox(root, textvariable=schedule_var, values=SCHEDULE_OPTIONS, state="readonly")
    schedule_dropdown.pack()
    schedule_dropdown.bind("<<ComboboxSelected>>", change_schedule_interval)

    # Developer Mode toggle (optional)
    if is_dev:
        dev_var = tk.BooleanVar()
        dev_var.set(config_data.get("developer_mode", False))
        def toggle_dev():
            config_data["developer_mode"] = dev_var.get()
        tk.Checkbutton(root, text="Enable Developer Mode", variable=dev_var, command=toggle_dev).pack(pady=(15, 0))

    # Submit and Save button
    def save_and_close():
        config_data["pc_folder"] = pc_entry.get()
        config_data["smartphone_folder"] = phone_entry.get()
        save_callback(config_data, profile_name)
        autostart_callback(config_data.get("autostart", False))
        root.destroy()

    tk.Button(root, text="💾 Save & Launch", command=save_and_close).pack(pady=(25, 10))

    root.mainloop()