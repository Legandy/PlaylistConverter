import os
import time
import traceback
import hashlib
import re
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ⚙️ Konfiguration
MAX_VERSIONS = 5
PROCESS_DELAY = 2
BLOCK_DURATION = 3
recently_processed = {}
recently_pushed_files = {}

# 📁 Ordnerstruktur
base = r"C:\#RSync\Audio\Playlists\PlaylistsAndre\MusicBee"
folders = {
    "library": os.path.join(base, "Library"),
    "conversion": os.path.join(base, "Conversion"),
    "android": os.path.join(base, "Android"),
    "logs": os.path.join(base, "Logs"),
}
log_path = os.path.join(folders["logs"], "log.txt")

def log(msg):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(folders["logs"], exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")
    print(msg)

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

def get_versioned_name(base_name):
    name, ext = os.path.splitext(base_name)
    versions = []
    for f in os.listdir(folders["conversion"]):
        if re.match(rf"{re.escape(name)}_v\d+{re.escape(ext)}", f):
            num = int(re.findall(r"_v(\d+)", f)[0])
            versions.append((num, f))
    next_num = max([v[0] for v in versions], default=0) + 1
    versions.sort()
    if len(versions) >= MAX_VERSIONS:
        for _, old_file in versions[:len(versions) - MAX_VERSIONS + 1]:
            os.remove(os.path.join(folders["conversion"], old_file))
            log(f"🗑️ Alte Version gelöscht: {old_file}")
    return f"{name}_v{next_num}{ext}"

def should_process(path):
    name = os.path.basename(path)
    now = time.time()
    if name in recently_processed and (now - recently_processed[name] < PROCESS_DELAY):
        return False
    recently_processed[name] = now
    return True

def process_to_conversion(src_path, origin):
    try:
        if os.path.commonpath([src_path, folders["conversion"]]) == folders["conversion"]:
            log(f"⏭️ Datei liegt bereits in Conversion: {src_path}")
            return

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
        cleaned_current = clean_for_hash(converted)
        new_hash = checksum(cleaned_current)

        existing = sorted([
            f for f in os.listdir(folders["conversion"])
            if f.startswith(clean_name + "_v") and f.endswith(".m3u")
        ], key=lambda x: int(re.search(r"_v(\d+)", x).group(1)), reverse=True)

        if existing:
            last_path = os.path.join(folders["conversion"], existing[0])
            with open(last_path, "r", encoding="utf-8") as f_last:
                last_lines = f_last.readlines()
            cleaned_last = clean_for_hash(last_lines)
            last_hash = checksum(cleaned_last)
            if new_hash == last_hash:
                log(f"🛑 Keine Änderung – Hash identisch zu letzter Version: {clean_name}")
                return

        versioned_name = get_versioned_name(clean_name)
        conv_path = os.path.join(folders["conversion"], versioned_name)
        with open(conv_path, "w", encoding="utf-8") as f_out:
            f_out.write("".join(converted))

        log(f"🔁 {origin} → Conversion: {versioned_name}")
        log(f"🔐 Prüfsumme: {new_hash}")
        push_from_conversion(conv_path)
    except Exception as e:
        log(f"🚨 Fehler bei process_to_conversion: {traceback.format_exc()}")

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
        log(f"🚨 Fehler bei push_from_conversion: {traceback.format_exc()}")    

def initial_sync(folder_key, label):
    for file in os.listdir(folders[folder_key]):
        if file.endswith(".m3u") and not re.search(r"_v\d+\.m3u$", file):
            block_until = recently_pushed_files.get(folder_key, {}).get(file, 0)
            if time.time() < block_until:
                log(f"⏸️ Initialsync gesperrt für {file} in {label}")
                continue
            full_path = os.path.join(folders[folder_key], file)
            log(f"🆕 Initialsync aus {label}: {file}")
            process_to_conversion(full_path, label)

class WatchHandler(FileSystemEventHandler):
    def __init__(self, label): self.label = label

    def handle_event(self, event):
        if not event.is_directory and event.src_path.endswith(".m3u"):
            file_name = os.path.basename(event.src_path)
            folder_key = self.label.lower()
            skip_until = recently_pushed_files.get(folder_key, {}).get(file_name, 0)
            if time.time() < skip_until:
                log(f"⏸️ Watchdog gesperrt für {file_name} in {self.label}")
                return
            if should_process(event.src_path):
                log(f"🆕 Event in {self.label}: {file_name}")
                process_to_conversion(event.src_path, self.label)

    def on_created(self, event): self.handle_event(event)
    def on_modified(self, event): self.handle_event(event)

# 🚀 Start
initial_sync("library", "Library")
initial_sync("android", "Android")
time.sleep(2)

observer = Observer()
observer.schedule(WatchHandler("Library"), folders["library"], recursive=True)
observer.schedule(WatchHandler("Android"), folders["android"], recursive=True)
observer.start()
log("🎧 Watchdog aktiv – warte auf Events.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    log("🛑 Beendet durch Nutzer.")
observer.join()
input("📥 Enter zum Schließen...")