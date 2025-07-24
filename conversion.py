import os
import re
import time
import traceback
import hashlib
from dataclasses import dataclass
from datetime import datetime

# === Sync Settings ===
@dataclass
class SyncConfig:
    delay: float
    block_duration: float
    max_backups: int

# === Folder Paths (initialized at runtime) ===
folders = {
    "smartphone": "",
    "pc": "",
    "conversion": os.path.join(os.path.dirname(__file__), "Conversion"),
    "backups": os.path.join(os.path.dirname(__file__), "Backups"),
    "logs": os.path.join(os.path.dirname(__file__), "Logs"),
}

recently_processed = {}
recently_pushed_files = {}

# === Logging ===
def log(msg, log_func=None):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{stamp}] {msg}"
    log_filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    log_path = os.path.join(folders["logs"], log_filename)
    os.makedirs(folders["logs"], exist_ok=True)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"🚨 Log error: {e}")
    print(full_msg)
    if log_func:
        log_func(full_msg)

# === Utilities ===
def strip_version(name):
    return re.sub(r"(_v\d+)+(?=\.m3u$)", "", name)

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
        if line.strip()
        and not any(
            line.lstrip().startswith(tag)
            for tag in ["# Generated on", "# Source Folder", "# Target Folder"]
        )
    )

def should_process(path, cfg: SyncConfig, verbose=False):
    name = os.path.basename(path)
    now = time.time()
    if name in recently_processed:
        delta = now - recently_processed[name]
        if delta < cfg.delay:
            if verbose:
                log(f"⏱️ Skipping {name}: triggered too soon ({delta:.2f}s)", None)
            return False
    recently_processed[name] = now
    return True

def convert_m3u8_to_m3u(folder_path, log_func=None, dry_run=False, verbose=False):
    log("🔎 Scanning for .m3u8 files...", log_func)
    for file in os.listdir(folder_path):
        if file.endswith(".m3u8"):
            original = os.path.join(folder_path, file)
            renamed = os.path.join(folder_path, file[:-5] + ".m3u")
            if dry_run:
                log(f"🧪 [DRY-RUN] Would rename: {file}", log_func)
                continue
            try:
                os.rename(original, renamed)
                log(f"📝 Renamed .m3u8 → .m3u: {file}", log_func)
            except Exception as e:
                log(f"🚨 Rename failed: {file} — {e}", log_func)

def create_backup(clean_name, content, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"{clean_name}_{timestamp}.m3u"
    backup_path = os.path.join(folders["backups"], backup_name)

    if dry_run:
        log(f"🧪 [DRY-RUN] Would create backup: {backup_name}", log_func)
        return

    try:
        with open(backup_path, "w", encoding="utf-8") as b:
            b.write(content)
        log(f"💾 Backup created: {backup_name}", log_func)
    except Exception as e:
        log(f"🚨 Backup failed — {e}", log_func)

    backups = sorted(
        [
            f
            for f in os.listdir(folders["backups"])
            if f.startswith(clean_name + "_") and f.endswith(".m3u")
        ],
        key=lambda x: os.path.getmtime(os.path.join(folders["backups"], x)),
    )

    if len(backups) > cfg.max_backups:
        for old_file in backups[: len(backups) - cfg.max_backups]:
            if dry_run:
                log(f"🧪 [DRY-RUN] Would delete old backup: {old_file}", log_func)
            else:
                os.remove(os.path.join(folders["backups"], old_file))
                log(f"🗑️ Deleted old backup: {old_file}", log_func)

def process_to_conversion(src_path, origin, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False, dev_mode=False):
    try:
        if not should_process(src_path, cfg, verbose):
            return

        rel_folder = folders["pc"] if origin == "PC" else folders["smartphone"]
        with open(src_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        log(f"📂 Reading file: {os.path.basename(src_path)}", log_func)
        clean_name = strip_version(os.path.basename(src_path))

        filtered_lines = [
            line
            for line in lines
            if not any(
                line.startswith(tag)
                for tag in ["# Generated on", "# Source Folder", "# Target Folder"]
            )
        ]

        converted = [
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"# Source Folder: {origin}\n",
            f"# Target Folder: {'Smartphone' if origin == 'PC' else 'PC'}\n",
        ]
        converted += [make_relative(line, rel_folder) + "\n" for line in filtered_lines]

        if dev_mode:
            converted.append("# 💡 [DEV] Injected test line\n")

        content = "".join(converted)
        create_backup(clean_name, content, cfg, log_func, dry_run=dry_run, verbose=verbose)

        cleaned_current = clean_for_hash([line.rstrip("\n") for line in converted])
        new_hash = checksum(cleaned_current)

        conv_path = os.path.join(folders["conversion"], clean_name)
        if dry_run:
            log(f"🧪 [DRY-RUN] Would write to Conversion: {clean_name}", log_func)
        else:
            with open(conv_path, "w", encoding="utf-8") as f:
                f.write(content)

        log(f"✅ Converted and backed up: {clean_name} from {origin}", log_func)
        if verbose:
            log(f"📎 Checksum: {new_hash}", log_func)

    except Exception as e:
        log(f"🚨 Error converting {src_path} — {e}", log_func)
        traceback.print_exc()

def push_from_conversion(conv_path, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False, dev_mode=False):
    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        raw_name = os.path.basename(conv_path)
        clean_name = strip_version(raw_name)

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#") and stripped:
                folder_key = (
                    "smartphone"
                    if "/PC/" in stripped or stripped.startswith("..")
                    else "pc"
                )
                target_folder = folders[folder_key]
                target_path = os.path.join(target_folder, clean_name)

                if dry_run:
                    log(f"🧪 [DRY-RUN] Would push to {folder_key}: {clean_name}", log_func)
                    return

                with open(target_path, "w", encoding="utf-8") as out:
                    out.writelines(lines)

                if folder_key not in recently_pushed_files:
                    recently_pushed_files[folder_key] = {}
                recently_pushed_files[folder_key][clean_name] = time.time() + cfg.block_duration
                recently_processed[clean_name] = time.time()

                log(f"📤 Pushed to {folder_key.capitalize()}: {clean_name}", log_func)
                return
    except Exception as e:
        log(f"🚨 Push error — {e}", log_func)
        traceback.print_exc()

def initial_sync_with_comparison(cfg: SyncConfig, log_func=None, dry_run=False, verbose=False, dev_mode=False):
    convert_m3u8_to_m3u(folders["pc"], log_func, dry_run=dry_run, verbose=verbose)
    convert_m3u8_to_m3u(folders["smartphone"], log_func, dry_run=dry_run, verbose=verbose)

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
                            log(f"✅ No change in {label}: {file}", log_func)
                            continue

                    log(f"🆕 Sync needed from {label}: {file}", log_func)
                    process_to_conversion(full_path, label, cfg, log_func, dry_run=dry_run, verbose=verbose, dev_mode=dev_mode)

                except Exception as e:
                    log(f"🚨 Sync error [{file}] — {e}", log_func)
                    traceback.print_exc()

from watchdog.events import FileSystemEventHandler

class WatchHandler(FileSystemEventHandler):
    def __init__(self, label, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False, dev_mode=False):
        self.label = label
        self.cfg = cfg
        self.log_func = log_func
        self.dry_run = dry_run
        self.verbose = verbose
        self.dev_mode = dev_mode

    def handle_event(self, event):
        if event.is_directory:
            return

        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext not in [".m3u", ".m3u8"]:
            return

        log(f"📄 Change detected in {self.label}: {path}", self.log_func)

        try:
            if self.label == "PC":
                if should_process(path, self.cfg, self.verbose):
                    process_to_conversion(path, origin="PC", cfg=self.cfg, log_func=self.log_func,
                                          dry_run=self.dry_run, verbose=self.verbose, dev_mode=self.dev_mode)
            elif self.label == "Smartphone":
                if should_process(path, self.cfg, self.verbose):
                    push_from_conversion(path, cfg=self.cfg, log_func=self.log_func,
                                         dry_run=self.dry_run, verbose=self.verbose, dev_mode=self.dev_mode)
        except Exception as e:
            log(f"🚨 Error handling file — {e}", self.log_func)
            traceback.print_exc()

    def on_created(self, event): self.handle_event(event)
    def on_modified(self, event): self.handle_event(event)