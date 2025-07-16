import os
import time
import traceback
import hashlib
import re
import threading
import sys
import platform
import json
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image
import subprocess

# === Configuration ===
#PROCESS_DELAY = 2       # Debounce time to avoid rapid reprocessing
#BLOCK_DURATION = 3      # Ignore window after pushing a file

# === Config File Path ===
config_path = os.path.join(os.path.dirname(__file__), "config.json")

# === Autostart ===
def setup_windows_autostart():
    startup_dir = os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs\Startup")
    bat_path = os.path.join(startup_dir, "PlaylistConverter_Autostart.bat")
    script_path = os.path.abspath(__file__)
    bat_content = f'@echo off\nstart "" "{script_path}"\n'

    try:
        with open(bat_path, "w") as bat_file:
            bat_file.write(bat_content)
        log(f"✅ Windows autostart created at: {bat_path}")
    except Exception as e:
        log(f"🚨 Failed to create Windows autostart: {e}")

def remove_windows_autostart():
    startup_dir = os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs\Startup")
    bat_path = os.path.join(startup_dir, "PlaylistConverter_Autostart.bat")
    try:
        if os.path.exists(bat_path):
            os.remove(bat_path)
            log("🗑️ Removed Windows autostart .bat")
    except Exception as e:
        log(f"🚨 Failed to remove Windows autostart: {e}")

def setup_linux_autostart():
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_path = os.path.join(autostart_dir, "playlistconverter.desktop")
    script_path = os.path.abspath(__file__)

    desktop_entry = f"""[Desktop Entry]
Type=Application
Exec=python3 "{script_path}"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=PlaylistConverter
Comment=m3u Playlist Converter for Absolute Paths to Relative Paths
"""

    try:
        with open(desktop_path, "w") as f:
            f.write(desktop_entry)
        log(f"✅ Linux autostart created at: {desktop_path}")
    except Exception as e:
        log(f"🚨 Failed to create Linux autostart: {e}")

def remove_linux_autostart():
    desktop_path = os.path.expanduser("~/.config/autostart/playlistconverter.desktop")
    try:
        if os.path.exists(desktop_path):
            os.remove(desktop_path)
            log("🗑️ Removed Linux autostart .desktop")
    except Exception as e:
        log(f"🚨 Failed to remove Linux autostart: {e}")

# === Autostart Prompt===

def setup_autostart_prompt():
    system = platform.system()
    print(f"\n🧩 Autostart Setup ({system})")
    choice = input("Would you like PlaylistConverter to run automatically on startup? (y/n): ").strip().lower()

    if choice != 'y':
        log("🛑 Autostart setup skipped by user")
        return

    if system == "Windows":
        setup_windows_autostart()
    elif system == "Linux":
        setup_linux_autostart()
    else:
        log(f"⚠️ Autostart not supported on: {system}")

# === Load Config from File ===
def load_config():
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        log("✅ Configuration loaded from config.json")
        return config
    except Exception as e:
        log(f"⚠️ No valid config found — entering setup: {e}")
        return None

# === Save Config to File ===
def save_config(config):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        log("💾 Configuration saved to config.json")
    except Exception as e:
        log(f"🚨 Failed to save config: {e}")

# === Interactive Setup ===
def get_user_config():
    print("🎧 PlaylistConverter Setup")
    print("Please enter the full path to your playlist base folder.")
    print("Example: C:\\Users\\YourName\\Playlists\n")

    base = input("📂 Base folder path: ").strip()
    if not os.path.isdir(base):
        print(f"🚨 Folder not found: {base}")
        sys.exit(1)

    print("\n💾 How many backups should be kept per playlist?")
    print("Enter a number like 3, 5, or 10 (default is 10)")
    try:
        max_backups = int(input("🔢 Max backups: ").strip())
    except ValueError:
        max_backups = 10
        print("⚠️ Invalid input — using default: 10")

    print("\n⏱️ Process delay in seconds (default is 2)")
    try:
        process_delay = float(input("⏳ Process delay: ").strip())
    except ValueError:
        process_delay = 2
        print("⚠️ Invalid input — using default: 2")

    print("\n🚫 Block duration after push in seconds (default is 2)")
    try:
        block_duration = float(input("🕒 Block duration: ").strip())
    except ValueError:
        block_duration = 2
        print("⚠️ Invalid input — using default: 2")

    print("\n🧩 Enable autostart on system startup?")
    enable_autostart = input("Run PlaylistConverter automatically when you log in? (y/n): ").strip().lower() == 'y'

    return {
        "base": base,
        "max_backups": max_backups,
        "process_delay": process_delay,
        "block_duration": block_duration,
        "enable_autostart": enable_autostart
    }


# === Load or Create Config ===
config = load_config()
if not config:
    config = get_user_config()
    save_config(config)


# === Unpack Config ===
if not os.path.isdir(config["base"]):
    log(f"🚨 Invalid base folder in config: {config['base']}")
    config = get_user_config()
    save_config(config)

base = config["base"]
MAX_BACKUPS = config["max_backups"]
PROCESS_DELAY = config["process_delay"]
BLOCK_DURATION = config["block_duration"]
ENABLE_AUTOSTART_PROMPT = config["enable_autostart"]

# === Folder Paths ===
folders = {
    "library": os.path.join(base, "Library"),
    "conversion": os.path.join(base, "Conversion"),
    "android": os.path.join(base, "Android"),
    "logs": os.path.join(base, "Logs"),
    "backups": os.path.join(base, "Backups"),
}
log_path = os.path.join(folders["logs"], "log.txt")

# Ensure folders exist
for path in folders.values():
    os.makedirs(path, exist_ok=True)

# === Internal Caches ===
recently_processed = {}
recently_pushed_files = {}

# === Logging ===
def log(msg):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")
    print(msg)

# === Autostart Setup ===
system = platform.system()

if ENABLE_AUTOSTART_PROMPT:
    if system == "Windows":
        setup_windows_autostart()
    elif system == "Linux":
        setup_linux_autostart()
else:
    if system == "Windows":
        remove_windows_autostart()
    elif system == "Linux":
        remove_linux_autostart()

# === Utilities ===
def convert_m3u8_to_m3u(folder_path):
    for file in os.listdir(folder_path):
        if file.endswith(".m3u8"):
            original = os.path.join(folder_path, file)
            renamed = os.path.join(folder_path, file[:-5] + ".m3u")
            try:
                os.rename(original, renamed)
                log(f"📝 Renamed .m3u8 → .m3u: {file}")
            except Exception as e:
                log(f"🚨 Failed to rename {file}: {e}")
def strip_version(name):
    return re.sub(r'(_v\d+)+(?=\.m3u$)', '', name)

def make_relative(line, base_path):
    line = line.strip()
    if line.startswith("#") or not line:
        return line
    try:
        return os.path.normpath(os.path.relpath(line, base_path)).replace("\\", "/")
    except:
        return line

def checksum(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def clean_for_hash(lines):
    return "\n".join(
        line.strip()
        for line in lines
        if line.strip() and not any(
            line.lstrip().startswith(tag)
            for tag in ["# Generated on", "# Source Folder", "# Target Folder"]
        )
    )

def should_process(path):
    name = os.path.basename(path)
    now = time.time()
    if name in recently_processed and (now - recently_processed[name] < PROCESS_DELAY):
        return False
    recently_processed[name] = now
    return True

def create_backup(clean_name, content):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"{clean_name}_{timestamp}.m3u"
    backup_path = os.path.join(folders["backups"], backup_name)

    with open(backup_path, "w", encoding="utf-8") as b:
        b.write(content)
    log(f"💾 Backup created: {backup_name}")

    # Remove old backups if limit exceeded
    backups = sorted([
        f for f in os.listdir(folders["backups"])
        if f.startswith(clean_name + "_") and f.endswith(".m3u")
    ], key=lambda x: os.path.getmtime(os.path.join(folders["backups"], x)))

    if len(backups) > MAX_BACKUPS:
        for old_file in backups[:len(backups) - MAX_BACKUPS]:
            os.remove(os.path.join(folders["backups"], old_file))
            log(f"🗑️ Old backup deleted: {old_file}")

# === Core Processing ===
def process_to_conversion(src_path, origin):
    try:
        raw_name = os.path.basename(src_path)
        clean_name = strip_version(raw_name)
        rel_folder = folders["library"] if origin == "Library" else folders["android"]

        with open(src_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filtered_lines = [line for line in lines if not any(
            line.startswith(tag) for tag in ["# Generated on", "# Source Folder", "# Target Folder"]
        )]

        converted = [
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"# Source Folder: {origin}\n",
            f"# Target Folder: {'Android' if origin == 'Library' else 'Library'}\n"
        ]
        converted += [make_relative(line, rel_folder) + "\n" for line in filtered_lines]
        content = "".join(converted)

        cleaned_current = clean_for_hash([line.rstrip("\n") for line in converted])
        new_hash = checksum(cleaned_current)

        conv_path = os.path.join(folders["conversion"], clean_name)

        if os.path.exists(conv_path):
            with open(conv_path, "r", encoding="utf-8") as f_conv:
                conv_lines = f_conv.readlines()
            cleaned_conv = clean_for_hash([line.rstrip("\n") for line in conv_lines])
            if new_hash == checksum(cleaned_conv):
                log(f"✅ No change detected — skipping: {clean_name}")
                return

        with open(conv_path, "w", encoding="utf-8") as f_out:
            f_out.write(content)

        log(f"🔁 {origin} → Conversion updated: {clean_name}")
        log(f"🔐 Hash: {new_hash}")
        create_backup(clean_name, content)
        push_from_conversion(conv_path)

    except Exception as e:
        log(f"🚨 Error in process_to_conversion:\n{traceback.format_exc()}")

# === Push Conversion to Target Folder ===
def push_from_conversion(conv_path):
    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        raw_name = os.path.basename(conv_path)
        clean_name = strip_version(raw_name)

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#") and stripped:
                folder_key = "android" if "/Library/" in stripped or stripped.startswith("..") else "library"
                target_folder = folders[folder_key]
                target_path = os.path.join(target_folder, clean_name)
                with open(target_path, "w", encoding="utf-8") as out:
                    out.writelines(lines)
                if folder_key not in recently_pushed_files:
                    recently_pushed_files[folder_key] = {}
                recently_pushed_files[folder_key][clean_name] = time.time() + BLOCK_DURATION
                recently_processed[clean_name] = time.time()
                log(f"📤 Conversion → {folder_key.capitalize()}: {clean_name}")
                return
    except Exception as e:
        log(f"🚨 Error in push_from_conversion:\n{traceback.format_exc()}")

# === Initial Sync with Hash Comparison ===
convert_m3u8_to_m3u(folders["android"])
def initial_sync_with_comparison():
    for folder_key, label in [("android", "Android"), ("library", "Library")]:
        for file in os.listdir(folders[folder_key]):
            if file.endswith(".m3u") and not re.search(r"_v\d+\.m3u$", file):
                full_path = os.path.join(folders[folder_key], file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    cleaned_current = clean_for_hash([line.rstrip("\n") for line in lines])
                    current_hash = checksum(cleaned_current)

                    conv_path = os.path.join(folders["conversion"], strip_version(file))
                    if os.path.exists(conv_path):
                        with open(conv_path, "r", encoding="utf-8") as f_conv:
                            conv_lines = f_conv.readlines()
                        cleaned_conv = clean_for_hash([line.rstrip("\n") for line in conv_lines])
                        if current_hash == checksum(cleaned_conv):
                            log(f"✅ No change in {label}: {file}")
                            continue

                    log(f"🆕 Initial sync from {label}: {file}")
                    process_to_conversion(full_path, label)

                except Exception as e:
                    log(f"🚨 Initial sync error [{file}]:\n{traceback.format_exc()}")

# === Watchdog Setup ===
class WatchHandler(FileSystemEventHandler):
    def __init__(self, label): self.label = label

    def handle_event(self, event):
        if not event.is_directory and event.src_path.endswith(".m3u"):
            file_name = os.path.basename(event.src_path)
            folder_key = self.label.lower()
            skip_until = recently_pushed_files.get(folder_key, {}).get(file_name, 0)
            if time.time() < skip_until:
                log(f"⏸️ Watchdog blocked for {file_name} in {self.label}")
                return
            if should_process(event.src_path):
                log(f"✏️ Watchdog triggered in {self.label}: {file_name}")
                process_to_conversion(event.src_path, self.label)

    def on_created(self, event): self.handle_event(event)
    def on_modified(self, event): self.handle_event(event)


# === Tray Icon Setup ===

def on_run():
    log("▶️ Manual sync triggered from tray")
    initial_sync_with_comparison()

def on_quit(icon):
    observer.stop()
    observer.join()
    log("🛑 Tray app quit by user.")
    icon.stop()

def open_base_folder(icon=None, item=None):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(base)
        elif system == "Linux":
            subprocess.Popen(["xdg-open", base])
        elif system == "Darwin":
            subprocess.Popen(["open", base])
        log(f"📂 Opened base folder: {base}")
    except Exception as e:
        log(f"🚨 Failed to open base folder: {e}")

def toggle_autostart(icon):
    config = load_config()
    if not config:
        log("⚠️ Cannot toggle autostart — config not found")
        return

    current = config.get("enable_autostart", False)
    new_state = not current
    config["enable_autostart"] = new_state
    save_config(config)

    system = platform.system()
    if new_state:
        if system == "Windows":
            setup_windows_autostart()
        elif system == "Linux":
            setup_linux_autostart()
        log("✅ Autostart enabled")
    else:
        if system == "Windows":
            remove_windows_autostart()
        elif system == "Linux":
            remove_linux_autostart()
        log("🛑 Autostart disabled")

    icon.update_menu()

def reset_setup(icon=None, item=None):
    try:
        confirm = input("⚠️ Are you sure you want to reset configuration? This will overwrite your current settings. (y/n): ").strip().lower()
        if confirm != 'y':
            log("🛑 Reset setup cancelled by user.")
            return

        new_config = get_user_config()
        save_config(new_config)

        # Apply new config immediately
        global base, MAX_BACKUPS, PROCESS_DELAY, BLOCK_DURATION, ENABLE_AUTOSTART_PROMPT
        base = new_config["base"]
        MAX_BACKUPS = new_config["max_backups"]
        PROCESS_DELAY = new_config["process_delay"]
        BLOCK_DURATION = new_config["block_duration"]
        ENABLE_AUTOSTART_PROMPT = new_config["enable_autostart"]

        # Apply autostart setting
        system = platform.system()
        if ENABLE_AUTOSTART_PROMPT:
            if system == "Windows":
                setup_windows_autostart()
            elif system == "Linux":
                setup_linux_autostart()
        else:
            if system == "Windows":
                remove_windows_autostart()
            elif system == "Linux":
                remove_linux_autostart()

        log("🔄 Configuration reset and applied.")

    except Exception as e:
        log(f"🚨 Failed to reset configuration: {e}")

def create_tray():
    system = platform.system()

    if system == "Darwin":
        log("🍎 Tray icon not supported on macOS — skipping tray setup")
        return

    if system == "Linux":
        log("🐧 Attempting tray setup on Linux — may vary by desktop")

    try:
        icon_path = os.path.join(os.path.dirname(__file__), "playlist_icon.ico")

        if not os.path.exists(icon_path):
            log("⚠️ Icon file not found — using fallback")
            image = Image.new('RGB', (64, 64), color='black')
        else:
            image = Image.open(icon_path)

        menu = Menu(
    Item('Run Sync', on_run),
    Item('Open Folder', open_base_folder),
    Item('Toggle Autostart', toggle_autostart),
    Item('Reset Setup', reset_setup),
    Item('Quit', on_quit)
)

        icon = Icon("PlaylistConverter", image, "Playlist Sync", menu)
        threading.Thread(target=icon.run, daemon=True).start()
        log(f"🎧 Tray created successfully on {system}")

    except Exception as e:
        log(f"🚨 Tray setup failed on {system}: {e}")


# === Startup ===
initial_sync_with_comparison()
time.sleep(2)

observer = Observer()
observer.schedule(WatchHandler("Library"), folders["library"], recursive=True)
observer.schedule(WatchHandler("Android"), folders["android"], recursive=True)
observer.start()
log("🎧 Watchdog is active. Monitoring changes...")

create_tray()  # 🖼️ Launch tray icon with menu

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    log("🛑 Stopped by user.")
observer.join()
#input("📥 Press Enter to exit...")