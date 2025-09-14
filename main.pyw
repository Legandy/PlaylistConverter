import argparse
import os
import threading
from config import load_config, apply_autostart_setting
from conversion import initial_sync_with_comparison, WatchHandler, folders, log
from scheduler import start_scheduler
from main_gui import launch_enhanced_main_gui as launch_main_gui  # Fixed import
from setup_gui import launch_setup_gui  # You'll need to create this or rename existing GUI file
from watchdog.observers import Observer
from conversion import SyncConfig

# Launches GUI setup interface when --setup flag is used
def launch_setup(profile="default"):
    def save_callback(data, profile_name):
        from config import save_config
        save_config(data, profile_name)

    launch_setup_gui(
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
    parser.add_argument("--gui", action="store_true", help="Launch main GUI window")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry-run mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dev", action="store_true", help="Enable developer mode")
    parser.add_argument("--profile", type=str, default="default", help="Config profile to load")
    parser.add_argument("--tray", action="store_true", help="Run in system tray mode")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray (console mode)")
    parser.add_argument("--console", action="store_true", help="Force console mode")

    global args
    args = parser.parse_args()

    # === Launch Setup GUI if requested ===
    if args.setup:
        launch_setup(profile=args.profile)
        return

    # === Launch Main GUI if requested ===
    if args.gui:
        launch_main_gui(profile=args.profile)
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

    # === Decide on UI Mode ===
    use_tray = False
    use_gui = False
    use_console = False
    
    # Explicit mode selection
    if args.tray:
        use_tray = True
    elif args.console or args.no_tray:
        use_console = True
    elif args.verbose or args.dev or args.dry_run:
        # Development/debug modes prefer console
        use_console = True
    else:
        # Auto-detect best mode
        try:
            import pystray
            # Check if we're in a GUI environment
            if os.name == 'nt' or os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
                use_tray = True
            else:
                use_console = True
        except ImportError:
            log("ℹ️ pystray not available - using console mode")
            use_console = True

    # === Launch Appropriate Mode ===
    if use_tray:
        # System Tray Mode
        log("🖥️ Starting in system tray mode...")
        log("💡 Right-click the tray icon for options")
        log("💡 Use --gui flag to open the main window directly")
        
        try:
            from tray import start_tray_with_watchdog  # Fixed import
            start_tray_with_watchdog(
                cfg, config, 
                profile=args.profile,
                is_dev=args.dev, 
                dry_run=args.dry_run, 
                verbose=args.verbose
            )
        except ImportError:
            log("⚠️ Tray module not available - falling back to console mode")
            use_console = True
    
    if use_console:
        # Console Mode
        log("💻 Starting in console mode...")
        log("💡 Use --gui to open the graphical interface")
        log("💡 Use --tray to run in system tray")
        
        if config.get("use_watchdog", True):
            log("🟢 Real-time folder sync active (Watchdog)...")
            log("💡 Press Ctrl+C to stop")
            launch_main(cfg, config, is_dev=args.dev, dry_run=args.dry_run, verbose=args.verbose)
        else:
            log("🔕 Watchdog disabled — relying on scheduler only")
            
            # Keep alive for scheduler
            if config.get("schedule_interval", "").lower() != "never":
                log("⏰ Scheduler active - press Ctrl+C to stop")
                try:
                    while True:
                        pass
                except KeyboardInterrupt:
                    log("👋 Shutting down...")
            else:
                log("✅ Initial sync complete - no background services enabled")

if __name__ == "__main__":
    main()