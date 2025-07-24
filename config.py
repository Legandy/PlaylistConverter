import os
import json

# Default configuration values used when loading or initializing a new config file
DEFAULT_CONFIG = {
    "pc_folder": "",
    "smartphone_folder": "",
    "max_backups": 5,
    "process_delay": 1.0,
    "block_duration": 2.0,
    "max_logs": 10,
    "autostart": False,
    "use_watchdog": True,
    "schedule_interval": "",  # e.g. "30min", "hourly", "daily@02:00"
    "developer_mode": False,
    "log_level": "info"
}

# Returns the file path for the given config profile
def config_path(profile="default"):
    suffix = f"_{profile}.json" if profile != "default" else ".json"
    return os.path.join(os.path.dirname(__file__), f"config{suffix}")

# Loads configuration from disk and injects missing keys from DEFAULT_CONFIG
def load_config(profile="default"):
    path = config_path(profile)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, default_val in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = default_val
        return data
    except Exception as e:
        print(f"🚨 Failed to load config [{profile}]: {e}")
        return None

# Saves configuration dictionary to disk for the specified profile
def save_config(data, profile="default"):
    path = config_path(profile)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Config saved: {path}")
    except Exception as e:
        print(f"🚨 Failed to save config: {e}")

# Validates basic required fields in the config to ensure folders exist and values are positive
def validate_config(cfg):
    try:
        folders = [cfg["pc_folder"], cfg["smartphone_folder"]]
        if not all(os.path.isdir(folder) for folder in folders):
            return False
        floats = [cfg["process_delay"], cfg["block_duration"]]
        ints = [cfg["max_backups"], cfg["max_logs"]]
        if any(val < 0 for val in floats + ints):
            return False
        return True
    except:
        return False

# Enables or disables app launch on Windows startup by modifying a .bat file
def apply_autostart_setting(enabled):
    bat_path = os.path.join(os.path.dirname(__file__), "autostart.bat")
    startup_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    target_path = os.path.join(startup_dir, "PlaylistConverter.bat")
    try:
        if enabled:
            if not os.path.exists(bat_path):
                with open(bat_path, "w") as f:
                    f.write(f'start "" "{os.path.abspath("PlaylistConverter.pyw")}"\n')
            with open(target_path, "w") as f:
                f.write(f'start "" "{os.path.abspath("PlaylistConverter.pyw")}"\n')
            print("⚙️ Autostart enabled.")
        else:
            if os.path.exists(target_path):
                os.remove(target_path)
            print("⚙️ Autostart disabled.")
    except Exception as e:
        print(f"🚨 Autostart error: {e}")