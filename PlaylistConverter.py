import os
import time
import traceback
import hashlib
import re
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === Configuration ===
MAX_BACKUPS = 10
PROCESS_DELAY = 2
BLOCK_DURATION = 3

recently_processed = {}
recently_pushed_files = {}

# === Folder Paths ===
base = r"C:\#RSync\Audio\Playlists\PlaylistsAndre\MusicBee"
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

# === Logging ===
def log(msg):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")
    print(msg)

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

# === Startup ===
initial_sync_with_comparison()
time.sleep(2)

observer = Observer()
observer.schedule(WatchHandler("Library"), folders["library"], recursive=True)
observer.schedule(WatchHandler("Android"), folders["android"], recursive=True)
observer.start()
log("🎧 Watchdog is active. Monitoring changes...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    log("🛑 Stopped by user.")
observer.join()
input("📥 Press Enter to exit...")