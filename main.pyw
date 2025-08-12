# main.py - Updated main entry point with tray support
import argparse
import os
import threading
from config import load_config, apply_autostart_setting
from conversion import initial_sync_with_comparison, WatchHandler, folders, log
from scheduler import start_scheduler  # Fixed import (rename shedular.py to scheduler.py)
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

def main():
    """Main entry point for the application"""
    # === Argument Parsing ===
    parser = argparse.ArgumentParser(description="Playlist Converter")
    parser.add_argument("--setup", action="store_true", help="Open setup GUI")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry-run mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dev", action="store_true", help="Enable developer mode")
    parser.add_argument("--profile", type=str, default="default", help="Config profile to load")
    parser.add_argument("--tray", action="store_true", help="Run in system tray mode")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray (console mode)")

    global args
    args = parser.parse_args()

    # === Launch Setup GUI if requested ===
    if args.setup:
        launch_setup(profile=args.profile)
        return

    # === Load Config ===
    config = load_config(profile=args.profile)
    if not config:
        print("⚠️ Config missing — launch with --setup to configure.")
        return

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

    # === Decide on Tray vs Console Mode ===
    use_tray = False
    
    if args.tray:
        use_tray = True
    elif args.no_tray:
        use_tray = False
    else:
        # Auto-detect: use tray if available and not in verbose/dev mode
        try:
            import pystray
            use_tray = not (args.verbose or args.dev or args.dry_run)
        except ImportError:
            use_tray = False
            log("ℹ️ pystray not available - running in console mode")

    # === Launch Appropriate Mode ===
    if use_tray:
        # System Tray Mode - run watchdog in background thread
        log("🖥️ Starting in system tray mode...")
        
        if config.get("use_watchdog", True):
            def watchdog_thread():
                launch_main(cfg, config, is_dev=args.dev, dry_run=args.dry_run, verbose=args.verbose)
            
            threading.Thread(target=watchdog_thread, daemon=True).start()
        
        # Start tray (this blocks until quit)
        try:
            from tray import start_tray
            start_tray(profile=args.profile)
        except ImportError:
            log("⚠️ Tray module not available - falling back to console mode")
            use_tray = False
    
    if not use_tray:
        # Console Mode
        log("💻 Starting in console mode...")
        
        if config.get("use_watchdog", True):
            log("🟢 Real-time folder sync active (Watchdog)...")
            launch_main(cfg, config, is_dev=args.dev, dry_run=args.dry_run, verbose=args.verbose)
        else:
            log("🔕 Watchdog disabled — relying on scheduler or manual sync.")
            
            # Keep alive for scheduler
            if config.get("schedule_interval", "").lower() != "never":
                try:
                    while True:
                        pass
                except KeyboardInterrupt:
                    log("👋 Shutting down...")

if __name__ == "__main__":
    main()