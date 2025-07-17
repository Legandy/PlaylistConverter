import os
import json
import platform
import subprocess
import re
import hashlib
import time
import threading
import traceback
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image
from datetime import datetime

# === Script Directory ===
script_dir = os.path.dirname(os.path.abspath(__file__))

# === Config File Path ===
config_path = os.path.join(script_dir, "config.json")

# === Logging Path ===
log_dir = os.path.join(script_dir, "Logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.txt"
log_path = os.path.join(log_dir, log_filename)


# === Logging Function ===
def rotate_logs():
    try:
        logs = sorted([
            f for f in os.listdir(log_dir)
            if f.startswith("log_") and f.endswith(".txt")
        ], key=lambda x: os.path.getmtime(os.path.join(log_dir, x)))

        if len(logs) > MAX_LOGS:
            for old_log in logs[:len(logs) - MAX_LOGS]:
                os.remove(os.path.join(log_dir, old_log))
                print(f"🗑️ Old log deleted: {old_log}")
    except Exception as e:
        print(f"🚨 Log rotation error: {e}")

def log(msg):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    log_path = os.path.join(log_dir, log_filename)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {msg}\n")
    except Exception as e:
        print(f"🚨 Failed to write to log: {e}")
    print(msg)
    rotate_logs()


VERSION = "1.0.0"
log(f"🎧 PlaylistConverter v{VERSION} started")

# === Save Configuration Function ===
def save_config(config):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        log("💾 Configuration saved to config.json")
    except Exception as e:
        log(f"🚨 Failed to save config: {e}")

# === Configuration Prompt and Save ===
def get_user_config():
    print("🎧 PlaylistConverter Setup")
    sp_path = input("📱 Enter full path to smartphone playlist folder (e.g. D:/SP_Playlists): ").strip()
    pc_path = input("💻 Enter full path to PC playlist folder (e.g. C:/PC_Playlists): ").strip()
    max_backups = int(input("🔢 Max backups per playlist: ").strip())
    process_delay = float(input("⏳ Process delay (seconds): ").strip())
    block_duration = float(input("🕒 Block duration after push (seconds): ").strip())
    enable_autostart = input("⚙️ Enable autostart? (y/n): ").strip().lower() == 'y'
    max_logs = int(input("🧹 Max number of log files to keep: ").strip())

    config = {
        "sp_path": sp_path,
        "pc_path": pc_path,
        "max_backups": max_backups,
        "process_delay": process_delay,
        "block_duration": block_duration,
        "enable_autostart": enable_autostart,
        "max_logs": max_logs
    }

    save_config(config)
    return config

# === Load and Validate Configuration ===
def load_config():
    if not os.path.exists(config_path):
        return get_user_config()
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        log("✅ Configuration loaded from config.json")
        return config
    except Exception as e:
        log(f"⚠️ Failed to load config — entering setup: {e}")
        return get_user_config()

config = load_config()
for key in ["sp_path", "pc_path"]:
    if not os.path.isdir(config[key]):
        log(f"🚨 Invalid folder path in config: {config[key]}")
        config = get_user_config()
        break

# === Unpack Config and Create Folders ===
SP_PATH = config["sp_path"]
PC_PATH = config["pc_path"]
MAX_BACKUPS = config["max_backups"]
PROCESS_DELAY = config["process_delay"]
BLOCK_DURATION = config["block_duration"]
ENABLE_AUTOSTART_PROMPT = config["enable_autostart"]
MAX_LOGS = config["max_logs"]

folders = {
    "smartphone": SP_PATH,
    "pc": PC_PATH,
    "conversion": os.path.join(script_dir, "Conversion"),
    "backups": os.path.join(script_dir, "Backups"),
    "logs": log_dir
}

for name, path in folders.items():
    os.makedirs(path, exist_ok=True)
    log(f"📁 Ensured folder exists: {name} → {path}")

# === Autostart Functions ===
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
Comment=Playlist Sync Tool
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

def apply_autostart_setting(enabled):
    system = platform.system()
    if enabled:
        if system == "Windows":
            setup_windows_autostart()
        elif system == "Linux":
            setup_linux_autostart()
    else:
        if system == "Windows":
            remove_windows_autostart()
        elif system == "Linux":
            remove_linux_autostart()

apply_autostart_setting(ENABLE_AUTOSTART_PROMPT)

# === Tray menu Open App Folder Function ===
def open_app_folder(icon=None, item=None):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(script_dir)
        elif system == "Linux":
            subprocess.Popen(["xdg-open", script_dir])
        elif system == "Darwin":
            subprocess.Popen(["open", script_dir])
        log(f"📂 Opened app folder: {script_dir}")
    except Exception as e:
        log(f"🚨 Failed to open app folder: {e}")

# === Sync Logic and Convert M3U8 to M3U ===
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



# === Helper Functions ===
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

# === Create Backup Function ===
def create_backup(clean_name, content):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"{clean_name}_{timestamp}.m3u"
    backup_path = os.path.join(folders["backups"], backup_name)

    with open(backup_path, "w", encoding="utf-8") as b:
        b.write(content)
    log(f"💾 Backup created: {backup_name}")

    backups = sorted([
        f for f in os.listdir(folders["backups"])
        if f.startswith(clean_name + "_") and f.endswith(".m3u")
    ], key=lambda x: os.path.getmtime(os.path.join(folders["backups"], x)))

    if len(backups) > MAX_BACKUPS:
        for old_file in backups[:len(backups) - MAX_BACKUPS]:
            os.remove(os.path.join(folders["backups"], old_file))
            log(f"🗑️ Old backup deleted: {old_file}")

# === Process Playlist Conversion ===
def process_to_conversion(src_path, origin):
    try:
        raw_name = os.path.basename(src_path)
        clean_name = strip_version(raw_name)
        rel_folder = folders["pc"] if origin == "PC" else folders["smartphone"]

        with open(src_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filtered_lines = [line for line in lines if not any(
            line.startswith(tag) for tag in ["# Generated on", "# Source Folder", "# Target Folder"]
        )]

        converted = [
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"# Source Folder: {origin}\n",
            f"# Target Folder: {'Smartphone' if origin == 'PC' else 'PC'}\n"
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

# === Push Converted Playlists ===
def push_from_conversion(conv_path):
    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        raw_name = os.path.basename(conv_path)
        clean_name = strip_version(raw_name)

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#") and stripped:
                folder_key = "smartphone" if "/PC/" in stripped or stripped.startswith("..") else "pc"
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

# === Initial Sync with Comparison ===
def initial_sync_with_comparison():
    convert_m3u8_to_m3u(folders["pc"])
    convert_m3u8_to_m3u(folders["smartphone"])
    for folder_key, label in [("smartphone", "Smartphone"), ("pc", "PC")]:
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
recently_processed = {}
recently_pushed_files = {}

class WatchHandler(FileSystemEventHandler):
    def __init__(self, label):
        self.label = label

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



# === Tray Icon Functions ===
def on_run(): 
    log("▶️ Manual sync triggered")
    initial_sync_with_comparison()

def on_quit(icon):
    observer.stop()
    observer.join()
    log("🛑 Tray app quit by user.")
    icon.stop()

def toggle_autostart(icon):
    config = load_config()
    if not config: return
    new_state = not config.get("enable_autostart", False)
    config["enable_autostart"] = new_state
    save_config(config)
    apply_autostart_setting(new_state)
    log(f"{'✅ Enabled' if new_state else '🛑 Disabled'} autostart")
    icon.update_menu()

def reset_setup(icon=None, item=None):
    confirm = input("⚠️ Reset configuration? This will overwrite current settings. (y/n): ").strip().lower()
    if confirm != 'y':
        log("🛑 Reset cancelled.")
        return
    new_config = get_user_config()
    save_config(new_config)

    # ✅ Validate new paths
    for key in ["sp_path", "pc_path"]:
        if not os.path.isdir(new_config[key]):
            log(f"🚨 Invalid folder path after reset: {new_config[key]}")
            return

    # ✅ Unpack new config
    global SP_PATH, PC_PATH, MAX_BACKUPS, PROCESS_DELAY, BLOCK_DURATION, ENABLE_AUTOSTART_PROMPT
    SP_PATH = new_config["sp_path"]
    PC_PATH = new_config["pc_path"]
    MAX_BACKUPS = new_config["max_backups"]
    PROCESS_DELAY = new_config["process_delay"]
    BLOCK_DURATION = new_config["block_duration"]
    ENABLE_AUTOSTART_PROMPT = new_config["enable_autostart"]
    folders["smartphone"] = SP_PATH
    folders["pc"] = PC_PATH
    apply_autostart_setting(ENABLE_AUTOSTART_PROMPT)
    log("🔄 Configuration reset and applied.")
    

def open_app_folder(icon=None, item=None):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(script_dir)
        elif system == "Linux":
            subprocess.Popen(["xdg-open", script_dir])
        elif system == "Darwin":
            subprocess.Popen(["open", script_dir])
        log(f"📂 Opened app folder: {script_dir}")
    except Exception as e:
        log(f"🚨 Failed to open app folder: {e}")

def create_tray():
    try:
        icon_path = os.path.join(script_dir, "playlist_icon.ico")
        image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64), color='black')
        menu = Menu(
            Item('Run Sync', on_run),
            Item('Open App Folder', open_app_folder),
            Item('Toggle Autostart', toggle_autostart),
            Item('Reset Setup', reset_setup),
            Item('Quit', on_quit)
        )
        threading.Thread(target=icon.run, daemon=True).start()
        log("🎧 Tray created successfully")
    except Exception as e:
        log(f"🚨 Tray setup failed: {e}")


# === Startup ===
initial_sync_with_comparison()
time.sleep(2)

observer = Observer()
observer.schedule(WatchHandler("PC"), folders["pc"], recursive=True)
observer.schedule(WatchHandler("Smartphone"), folders["smartphone"], recursive=True)
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