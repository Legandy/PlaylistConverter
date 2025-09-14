# enhanced_conversion.py - Your conversion.py with conflict resolution integrated
import os
import re
import time
import traceback
import hashlib
from dataclasses import dataclass
from datetime import datetime
from conflict_resolver import ConflictResolver, ConflictResolution, PlaylistConflict

# === Your existing SyncConfig ===
@dataclass
class SyncConfig:
    delay: float
    block_duration: float
    max_backups: int
    # New conflict resolution settings
    conflict_resolution: ConflictResolution = ConflictResolution.MERGE_NO_DUPLICATES
    auto_resolve_conflicts: bool = True
    backup_before_resolve: bool = True

# === Your existing folder paths ===
folders = {
    "smartphone": "",
    "pc": "",
    "conversion": os.path.join(os.path.dirname(__file__), "Conversion"),
    "backups": os.path.join(os.path.dirname(__file__), "Backups"),
    "logs": os.path.join(os.path.dirname(__file__), "Logs"),
    "conflicts": os.path.join(os.path.dirname(__file__), "Conflicts"),  # New: conflict backups
}

recently_processed = {}
recently_pushed_files = {}

# Initialize conflict resolver
conflict_resolver = ConflictResolver()

# === Your existing logging function ===
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

# === Your existing utility functions ===
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
            for tag in ["# Generated on", "# Source Folder", "# Target Folder", "# Resolved on", "# Merged playlist"]
        )
    )

# === NEW: Conflict detection and handling ===
def detect_and_handle_conflicts(cfg: SyncConfig, log_func=None, dry_run=False, verbose=False):
    """Scan for conflicts between PC and smartphone versions"""
    os.makedirs(folders["conflicts"], exist_ok=True)
    
    conflicts_found = []
    
    # Get all playlist files from both folders
    pc_playlists = {}
    smartphone_playlists = {}
    
    try:
        for file in os.listdir(folders["pc"]):
            if file.endswith(".m3u"):
                clean_name = strip_version(file)
                pc_playlists[clean_name] = os.path.join(folders["pc"], file)
    except FileNotFoundError:
        log(f"⚠️ PC folder not found: {folders['pc']}", log_func)
        return []
    
    try:
        for file in os.listdir(folders["smartphone"]):
            if file.endswith(".m3u"):
                clean_name = strip_version(file)
                smartphone_playlists[clean_name] = os.path.join(folders["smartphone"], file)
    except FileNotFoundError:
        log(f"⚠️ Smartphone folder not found: {folders['smartphone']}", log_func)
        return []
    
    # Check for conflicts in common playlists
    common_playlists = set(pc_playlists.keys()) & set(smartphone_playlists.keys())
    
    for playlist_name in common_playlists:
        pc_path = pc_playlists[playlist_name]
        smartphone_path = smartphone_playlists[playlist_name]
        
        conflict = conflict_resolver.detect_conflict(pc_path, smartphone_path)
        if conflict:
            conflicts_found.append(conflict)
            
            if verbose:
                log(f"⚔️ Conflict detected: {playlist_name}", log_func)
                log(conflict_resolver.get_conflict_summary(conflict), log_func)
    
    if conflicts_found:
        log(f"⚔️ Found {len(conflicts_found)} playlist conflicts", log_func)
        
        # Handle conflicts based on configuration
        for conflict in conflicts_found:
            handle_single_conflict(conflict, cfg, log_func, dry_run, verbose)
    else:
        if verbose:
            log("✅ No conflicts detected", log_func)
    
    return conflicts_found

def handle_single_conflict(conflict: PlaylistConflict, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False):
    """Handle a single playlist conflict"""
    
    # Backup original versions before resolving
    if cfg.backup_before_resolve and not dry_run:
        backup_conflict_versions(conflict, log_func)
    
    if cfg.auto_resolve_conflicts:
        # Automatic resolution
        resolved_entries = conflict_resolver.resolve_conflict(conflict, cfg.conflict_resolution)
        
        if resolved_entries is not None:
            if dry_run:
                log(f"🧪 [DRY-RUN] Would resolve conflict: {conflict.playlist_name} using {cfg.conflict_resolution.value}", log_func)
                return
            
            # Write resolved version to conversion folder
            conv_path = os.path.join(folders["conversion"], conflict.playlist_name)
            conflict_resolver.write_resolved_playlist(resolved_entries, conv_path)
            
            log(f"✅ Auto-resolved conflict: {conflict.playlist_name} ({len([e for e in resolved_entries if not e.path.startswith('#')])} songs)", log_func)
            
            # Update recently processed to prevent immediate re-processing
            recently_processed[conflict.playlist_name] = time.time()
        else:
            log(f"⚠️ Could not auto-resolve conflict: {conflict.playlist_name}", log_func)
    else:
        # Manual resolution required
        log(f"❓ Manual resolution required for: {conflict.playlist_name}", log_func)
        log("💡 Use the GUI conflict resolver or set auto_resolve_conflicts=True", log_func)

def backup_conflict_versions(conflict: PlaylistConflict, log_func=None):
    """Create backups of both versions before resolving conflict"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = conflict.playlist_name.replace(".m3u", "")
        
        # Backup PC version
        pc_backup_name = f"{base_name}_PC_{timestamp}.m3u"
        pc_backup_path = os.path.join(folders["conflicts"], pc_backup_name)
        with open(pc_backup_path, 'w', encoding='utf-8') as f:
            f.write("# PC version backup before conflict resolution\n")
            for entry in conflict.pc_version:
                f.write(entry.path + '\n')
        
        # Backup smartphone version
        phone_backup_name = f"{base_name}_PHONE_{timestamp}.m3u"
        phone_backup_path = os.path.join(folders["conflicts"], phone_backup_name)
        with open(phone_backup_path, 'w', encoding='utf-8') as f:
            f.write("# Smartphone version backup before conflict resolution\n")
            for entry in conflict.smartphone_version:
                f.write(entry.path + '\n')
        
        log(f"💾 Backed up conflict versions: {pc_backup_name}, {phone_backup_name}", log_func)
        
    except Exception as e:
        log(f"🚨 Failed to backup conflict versions: {e}", log_func)

# === NEW: Duplicate detection and removal ===
def scan_for_duplicates(playlist_path: str, log_func=None, verbose=False):
    """Scan a single playlist for duplicates"""
    try:
        entries = conflict_resolver.parse_playlist_file(playlist_path)
        duplicates = conflict_resolver.find_duplicates(entries)
        
        if duplicates:
            total_duplicates = sum(len(indices) - 1 for indices in duplicates.values())
            
            if verbose:
                log(f"🔍 Found {total_duplicates} duplicates in {os.path.basename(playlist_path)}", log_func)
                for path, indices in duplicates.items():
                    log(f"  📄 '{path}' appears {len(indices)} times", log_func)
            
            return duplicates
    except Exception as e:
        log(f"🚨 Error scanning for duplicates in {playlist_path}: {e}", log_func)
    
    return {}

def remove_duplicates_from_playlist(playlist_path: str, cfg: SyncConfig, log_func=None, dry_run=False, verbose=False):
    """Remove duplicates from a playlist file"""
    try:
        # Parse current playlist
        entries = conflict_resolver.parse_playlist_file(playlist_path)
        original_count = len([e for e in entries if not e.path.startswith('#')])
        
        # Remove duplicates
        clean_entries = conflict_resolver.remove_duplicates(entries)
        clean_count = len([e for e in clean_entries if not e.path.startswith('#')])
        
        duplicates_removed = original_count - clean_count
        
        if duplicates_removed > 0:
            if dry_run:
                log(f"🧪 [DRY-RUN] Would remove {duplicates_removed} duplicates from {os.path.basename(playlist_path)}", log_func)
                return duplicates_removed
            
            # Create backup before modifying
            backup_name = f"{os.path.basename(playlist_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_dedup.m3u"
            backup_path = os.path.join(folders["backups"], backup_name)
            
            # Copy original to backup
            with open(playlist_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            # Write cleaned version
            conflict_resolver.write_resolved_playlist(clean_entries, playlist_path)
            
            log(f"✅ Removed {duplicates_removed} duplicates from {os.path.basename(playlist_path)}", log_func)
            log(f"💾 Backup saved: {backup_name}", log_func)
            
            return duplicates_removed
        else:
            if verbose:
                log(f"✅ No duplicates found in {os.path.basename(playlist_path)}", log_func)
            return 0
            
    except Exception as e:
        log(f"🚨 Error removing duplicates from {playlist_path}: {e}", log_func)
        return 0

def scan_all_playlists_for_duplicates(cfg: SyncConfig, log_func=None, dry_run=False, verbose=False):
    """Scan all playlists in both folders for duplicates"""
    log("🔍 Scanning all playlists for duplicates...", log_func)
    
    total_duplicates = 0
    processed_playlists = 0
    
    # Scan PC playlists
    try:
        for file in os.listdir(folders["pc"]):
            if file.endswith(".m3u"):
                playlist_path = os.path.join(folders["pc"], file)
                duplicates = scan_for_duplicates(playlist_path, log_func, verbose)
                
                if duplicates:
                    total_duplicates += sum(len(indices) - 1 for indices in duplicates.values())
                
                processed_playlists += 1
    except FileNotFoundError:
        log(f"⚠️ PC folder not found: {folders['pc']}", log_func)
    
    # Scan smartphone playlists  
    try:
        for file in os.listdir(folders["smartphone"]):
            if file.endswith(".m3u"):
                playlist_path = os.path.join(folders["smartphone"], file)
                duplicates = scan_for_duplicates(playlist_path, log_func, verbose)
                
                if duplicates:
                    total_duplicates += sum(len(indices) - 1 for indices in duplicates.values())
                
                processed_playlists += 1
    except FileNotFoundError:
        log(f"⚠️ Smartphone folder not found: {folders['smartphone']}", log_func)
    
    log(f"📊 Scanned {processed_playlists} playlists, found {total_duplicates} total duplicates", log_func)
    return total_duplicates

# === ENHANCED: Your existing sync function with conflict resolution ===
def initial_sync_with_comparison(cfg: SyncConfig, log_func=None, dry_run=False, verbose=False, dev_mode=False):
    """Enhanced version of your sync function with conflict resolution"""
    
    # First, detect and handle conflicts
    conflicts = detect_and_handle_conflicts(cfg, log_func, dry_run, verbose)
    
    # Then proceed with normal sync, but skip files that had conflicts
    conflict_files = {conflict.playlist_name for conflict in conflicts}
    
    # Your existing m3u8 conversion
    convert_m3u8_to_m3u(folders["pc"], log_func, dry_run=dry_run, verbose=verbose)
    convert_m3u8_to_m3u(folders["smartphone"], log_func, dry_run=dry_run, verbose=verbose)

    for folder_key, label in [("smartphone", "Smartphone"), ("pc", "PC")]:
        for file in os.listdir(folders[folder_key]):
            if file.endswith(".m3u") and not re.search(r"_v\d+\.m3u$", file):
                # Skip files that were just resolved from conflicts
                if file in conflict_files:
                    if verbose:
                        log(f"⏭️ Skipping {file} - just resolved conflict", log_func)
                    continue
                
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

# === Your existing utility functions (keeping them unchanged) ===
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

# === Your existing WatchHandler with conflict awareness ===
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
            # Check for potential conflicts before processing
            filename = os.path.basename(path)
            clean_name = strip_version(filename)
            
            # Check if this file exists in the other location
            other_folder = folders["smartphone"] if self.label == "PC" else folders["pc"]
            other_path = os.path.join(other_folder, filename)
            
            if os.path.exists(other_path):
                # Potential conflict - let the conflict resolver handle it
                conflict = conflict_resolver.detect_conflict(path, other_path)
                if conflict:
                    log(f"⚔️ Potential conflict detected for {filename}", self.log_func)
                    handle_single_conflict(conflict, self.cfg, self.log_func, self.dry_run, self.verbose)
                    return
            
            # No conflict, proceed with normal processing
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

# === NEW: Command-line interface for conflict management ===
def cli_conflict_management():
    """CLI interface for managing conflicts and duplicates"""
    
    print("🔧 PlaylistConverter - Conflict Management")
    print("=" * 50)
    
    # Load config
    from config import load_config
    config = load_config()
    
    if not config:
        print("❌ No configuration found. Run --setup first.")
        return
    
    folders["pc"] = config["pc_folder"] 
    folders["smartphone"] = config["smartphone_folder"]
    
    cfg = SyncConfig(
        delay=config["process_delay"],
        block_duration=config["block_duration"],
        max_backups=config["max_backups"]
    )
    
    while True:
        print("\nOptions:")
        print("1. Scan for conflicts")
        print("2. Scan for duplicates")
        print("3. Remove duplicates from all playlists")
        print("4. Analyze specific playlist")
        print("5. Set conflict resolution rule")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            conflicts = detect_and_handle_conflicts(cfg, verbose=True)
            if not conflicts:
                print("✅ No conflicts found!")
                
        elif choice == "2":
            total_dupes = scan_all_playlists_for_duplicates(cfg, verbose=True)
            print(f"\n📊 Total duplicates found: {total_dupes}")
            
        elif choice == "3":
            confirm = input("Remove duplicates from ALL playlists? (y/N): ").strip().lower()
            if confirm == 'y':
                total_removed = 0
                for folder_key in ["pc", "smartphone"]:
                    folder_path = folders[folder_key]
                    try:
                        for file in os.listdir(folder_path):
                            if file.endswith(".m3u"):
                                playlist_path = os.path.join(folder_path, file)
                                removed = remove_duplicates_from_playlist(playlist_path, cfg)
                                total_removed += removed
                    except FileNotFoundError:
                        pass
                print(f"✅ Removed {total_removed} duplicates total")
            
        elif choice == "4":
            playlist_name = input("Enter playlist filename: ").strip()
            
            # Try to find the playlist
            playlist_path = None
            for folder_key in ["pc", "smartphone"]:
                candidate = os.path.join(folders[folder_key], playlist_name)
                if os.path.exists(candidate):
                    playlist_path = candidate
                    break
            
            if playlist_path:
                stats = conflict_resolver.analyze_playlist(playlist_path)
                print(f"\n📊 Analysis of {playlist_name}:")
                print(f"Total lines: {stats['total_lines']}")
                print(f"Content entries: {stats['content_entries']}")
                print(f"Comment lines: {stats['comment_lines']}")
                print(f"Duplicate entries: {stats['duplicate_entries']}")
                print(f"Unique entries: {stats['unique_entries']}")
                
                if stats['duplicates_detail']:
                    print("\nDuplicate details:")
                    for path, indices in stats['duplicates_detail'].items():
                        print(f"  '{path}' appears {len(indices)} times")
            else:
                print(f"❌ Playlist not found: {playlist_name}")
                
        elif choice == "5":
            playlist_name = input("Enter playlist filename: ").strip()
            print("Resolution strategies:")
            for i, strategy in enumerate(ConflictResolution, 1):
                print(f"{i}. {strategy.value}")
            
            strategy_choice = input("Enter strategy number: ").strip()
            try:
                strategy_num = int(strategy_choice) - 1
                strategies = list(ConflictResolution)
                if 0 <= strategy_num < len(strategies):
                    selected_strategy = strategies[strategy_num]
                    conflict_resolver.set_conflict_rule(playlist_name, selected_strategy)
                    print(f"✅ Set rule for {playlist_name}: {selected_strategy.value}")
                else:
                    print("❌ Invalid strategy number")
            except ValueError:
                print("❌ Invalid input")
                
        elif choice == "6":
            break
            
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    # Demo the new features
    print("🔀 Enhanced Conversion with Conflict Resolution")
    print("=" * 60)
    
    # Example configuration
    cfg = SyncConfig(
        delay=1.0,
        block_duration=2.0,
        max_backups=5,
        conflict_resolution=ConflictResolution.MERGE_NO_DUPLICATES,
        auto_resolve_conflicts=True
    )
    
    # Demo conflict detection
    print("Demo: This would detect conflicts and merge playlists automatically")
    print("Key features added:")
    print("✅ Automatic conflict detection")
    print("✅ Smart playlist merging")
    print("✅ Duplicate removal")
    print("✅ Conflict backup system")
    print("✅ CLI management interface")
    print("\nTo use: python enhanced_conversion.py"):