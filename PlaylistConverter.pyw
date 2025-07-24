import argparse
import os
from config import load_config, apply_autostart_setting
from conversion import initial_sync_with_comparison, WatchHandler, folders, log
from scheduler import start_scheduler
from gui import launch_gui
from watchdog.observers import Observer
from conversion import SyncConfig

# Launches GUI setup interface when --setup flag is used
def launch_setup(profile="default"):
    def save_callback(data, profile_name):
        from config import save_config
        save_config(data, profile_name)

    launch_gui(
        save_callback=save_callback,
        autostart_callback=apply_autostart_setting,
        is_dev=args.dev,
        profile=profile
    )

# Launches main app with watchdog monitoring if enabled
def launch_main(cfg, config, is_dev=False, dry_run=False, verbose=False):
    pc_folder = config["pc_folder"]
    smartphone_folder = config["smartphone_folder"]

    folders["pc"] = pc_folder
    folders["smartphone"] = smartphone_folder

    observer = Observer()

    # Watch smartphone folder and push back to PC
    handler1 = WatchHandler("Smartphone", cfg, dry_run=dry_run, verbose=verbose, dev_mode=is_dev)
    observer.schedule(handler1, smartphone_folder, recursive=True)

    # Watch PC folder and push to smartphone
    handler2 = WatchHandler("PC", cfg, dry_run=dry_run, verbose=verbose, dev_mode=is_dev)
    observer.schedule(handler2, pc_folder, recursive=True)

    observer.start()
    log("🚀 Watchdog observers started.")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# === Argument Parsing ===
parser = argparse.ArgumentParser(description="Playlist Converter")
parser.add_argument("--setup", action="store_true", help="Open setup GUI")
parser.add_argument("--dry-run", action="store_true", help="Enable dry-run mode")
parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
parser.add_argument("--dev", action="store_true", help="Enable developer mode")
parser.add_argument("--profile", type=str, default="default", help="Config profile to load")

args = parser.parse_args()

# === Launch Setup GUI if requested ===
if args.setup:
    launch_setup(profile=args.profile)
    exit()

# === Load Config ===
config = load_config(profile=args.profile)
if not config:
    print("⚠️ Config missing — launch with --setup to configure.")
    exit()

# === Set Sync Parameters ===
apply_autostart_setting(config.get("autostart", False))

cfg = SyncConfig(
    delay=config["process_delay"],
    block_duration=config["block_duration"],
    max_backups=config["max_backups"]
)

folders["pc"] = config["pc_folder"]
folders["smartphone"] = config["smartphone_folder"]

# === Initial Sync Pass ===
initial_sync_with_comparison(
    cfg,
    dry_run=args.dry_run,
    verbose=args.verbose,
    dev_mode=args.dev
)

# === Start Scheduled Sync if Enabled ===
if config.get("schedule_interval", "").lower() != "never":
    start_scheduler(
        cfg,
        dry_run=args.dry_run,
        verbose=args.verbose,
        dev_mode=args.dev,
        interval=config["schedule_interval"]
    )

# === Start Watchdog if Enabled ===
if config.get("use_watchdog", True):
    log("🟢 Real-time folder sync active (Watchdog)...")
    launch_main(cfg, config, is_dev=args.dev, dry_run=args.dry_run, verbose=args.verbose)
else:
    log("🔕 Watchdog disabled — relying on scheduler or manual sync.")