import threading
import os
import sys
import time
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from config import load_config, apply_autostart_setting, save_config
from conversion import initial_sync_with_comparison, SyncConfig, folders, log
from gui_enhanced import launch_setup_gui, launch_main_gui

class PlaylistConverterTray:
    def __init__(self, profile="default"):
        self.profile = profile
        self.config = load_config(profile)
        self.icon = None
        self.main_window = None
        self.sync_stats = {
            "files_synced": 0,
            "last_sync": None,
            "errors": 0,
            "uptime_start": time.time()
        }
        self.setup_folders()
    
    def setup_folders(self):
        """Initialize folder paths from config"""
        if self.config:
            folders["pc"] = self.config["pc_folder"]
            folders["smartphone"] = self.config["smartphone_folder"]
    
    def create_icon(self, theme="dark"):
        """Create themed icon"""
        try:
            # Try to load existing icon
            icon_path = os.path.join(os.path.dirname(__file__), "playlist_icon.ico")
            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except:
            pass
        
        # Create themed fallback icon
        width = height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Choose colors based on theme
        if theme == "dark":
            primary_color = (255, 255, 255, 255)  # White
            secondary_color = (100, 149, 237, 255)  # Cornflower blue
        else:
            primary_color = (47, 79, 79, 255)  # Dark slate gray
            secondary_color = (0, 100, 200, 255)  # Blue
        
        # Draw a music note icon
        # Note head
        draw.ellipse([16, 35, 32, 51], fill=primary_color)
        # Note stem
        draw.rectangle([28, 15, 32, 43], fill=primary_color)
        # Note flag
        points = [(32, 15), (45, 20), (45, 25), (32, 22), (32, 25), (40, 28), (40, 32), (32, 30)]
        draw.polygon(points, fill=secondary_color)
        
        # Add small sync arrows
        # Right arrow
        draw.polygon([(45, 45), (50, 40), (50, 43), (55, 43), (55, 47), (50, 47), (50, 50)], fill=secondary_color)
        # Left arrow  
        draw.polygon([(19, 55), (14, 50), (14, 53), (9, 53), (9, 57), (14, 57), (14, 60)], fill=secondary_color)
        
        return image
    
    def run_sync(self, icon=None, item=None):
        """Manually trigger sync operation"""
        def sync_thread():
            try:
                if not self.config:
                    log("⚠️ No configuration found. Please run setup first.")
                    self.show_notification("No configuration found", "Please run setup first")
                    return
                
                cfg = SyncConfig(
                    delay=self.config["process_delay"],
                    block_duration=self.config["block_duration"],
                    max_backups=self.config["max_backups"]
                )
                
                log("🔄 Manual sync triggered from tray")
                self.show_notification("Sync Started", "Manual sync in progress...")
                
                initial_sync_with_comparison(cfg)
                
                self.sync_stats["files_synced"] += 1
                self.sync_stats["last_sync"] = time.time()
                
                log("✅ Manual sync completed")
                self.show_notification("Sync Complete", "Manual sync finished successfully")
                
            except Exception as e:
                self.sync_stats["errors"] += 1
                log(f"🚨 Manual sync failed: {e}")
                self.show_notification("Sync Failed", f"Error: {str(e)[:50]}...")
        
        threading.Thread(target=launch_window, daemon=True).start()
    
    def open_folder(self, icon=None, item=None):
        """Open the PC playlist folder in file explorer"""
        try:
            if self.config and self.config.get("pc_folder"):
                folder_path = self.config["pc_folder"]
                if os.path.exists(folder_path):
                    if sys.platform == "win32":
                        os.startfile(folder_path)
                    elif sys.platform == "darwin":
                        os.system(f'open "{folder_path}"')
                    else:
                        os.system(f'xdg-open "{folder_path}"')
                    log(f"📂 Opened folder: {folder_path}")
                else:
                    log("⚠️ PC folder path doesn't exist")
                    self.show_notification("Folder Not Found", "PC folder path doesn't exist")
            else:
                log("⚠️ No PC folder configured")
                self.show_notification("No Configuration", "Please configure folders first")
        except Exception as e:
            log(f"🚨 Failed to open folder: {e}")
            self.show_notification("Error", "Failed to open folder")
    
    def toggle_autostart(self, icon=None, item=None):
        """Toggle autostart setting"""
        try:
            if not self.config:
                log("⚠️ No configuration found")
                self.show_notification("No Configuration", "Please run setup first")
                return
            
            current_autostart = self.config.get("autostart", False)
            new_autostart = not current_autostart
            
            apply_autostart_setting(new_autostart)
            
            # Update config
            self.config["autostart"] = new_autostart
            save_config(self.config, self.profile)
            
            status = "enabled" if new_autostart else "disabled"
            log(f"⚙️ Autostart {status}")
            self.show_notification("Autostart Updated", f"Autostart {status}")
            
            # Update menu
            self.update_menu()
            
        except Exception as e:
            log(f"🚨 Failed to toggle autostart: {e}")
            self.show_notification("Error", "Failed to toggle autostart")
    
    def open_settings(self, icon=None, item=None):
        """Launch the setup GUI to reconfigure"""
        def setup_callback(data, profile_name):
            save_config(data, profile_name)
            self.config = data
            self.setup_folders()
            log("💾 Configuration updated from tray")
            self.show_notification("Settings Updated", "Configuration saved successfully")
            
            # Update icon theme if changed
            if "theme" in data:
                new_icon = self.create_icon(data["theme"])
                if self.icon:
                    self.icon.icon = new_icon
        
        def launch_setup():
            try:
                launch_setup_gui(
                    save_callback=setup_callback,
                    autostart_callback=apply_autostart_setting,
                    profile=self.profile
                )
            except Exception as e:
                log(f"🚨 Failed to launch setup: {e}")
                self.show_notification("Error", "Failed to open settings")
        
        threading.Thread(target=launch_setup, daemon=True).start()
    
    def show_logs(self, icon=None, item=None):
        """Open the logs folder"""
        try:
            logs_path = folders["logs"]
            if os.path.exists(logs_path):
                if sys.platform == "win32":
                    os.startfile(logs_path)
                elif sys.platform == "darwin":
                    os.system(f'open "{logs_path}"')
                else:
                    os.system(f'xdg-open "{logs_path}"')
                log(f"📋 Opened logs folder: {logs_path}")
            else:
                log("⚠️ Logs folder doesn't exist yet")
                self.show_notification("No Logs", "Logs folder doesn't exist yet")
        except Exception as e:
            log(f"🚨 Failed to open logs: {e}")
            self.show_notification("Error", "Failed to open logs")
    
    def show_stats(self, icon=None, item=None):
        """Show sync statistics"""
        uptime = int((time.time() - self.sync_stats["uptime_start"]) / 60)
        last_sync = "Never"
        if self.sync_stats["last_sync"]:
            last_sync = time.strftime("%H:%M", time.localtime(self.sync_stats["last_sync"]))
        
        stats_msg = f"""Sync Statistics:
Files Synced: {self.sync_stats['files_synced']}
Last Sync: {last_sync}
Uptime: {uptime}m
Errors: {self.sync_stats['errors']}"""
        
        self.show_notification("Statistics", stats_msg)
        log(f"📊 Statistics displayed - Files: {self.sync_stats['files_synced']}, Errors: {self.sync_stats['errors']}")
    
    def toggle_theme(self, icon=None, item=None):
        """Toggle between dark and light theme"""
        try:
            if not self.config:
                return
            
            current_theme = self.config.get("theme", "dark")
            new_theme = "light" if current_theme == "dark" else "dark"
            
            self.config["theme"] = new_theme
            save_config(self.config, self.profile)
            
            # Update icon
            new_icon = self.create_icon(new_theme)
            if self.icon:
                self.icon.icon = new_icon
            
            log(f"🎨 Theme changed to {new_theme}")
            self.show_notification("Theme Changed", f"Switched to {new_theme} theme")
            
        except Exception as e:
            log(f"🚨 Failed to toggle theme: {e}")
    
    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        log("👋 PlaylistConverter shutting down from tray")
        if self.icon:
            self.icon.stop()
        
        # Close main window if open
        if self.main_window and hasattr(self.main_window, 'root'):
            try:
                self.main_window.root.quit()
            except:
                pass
    
    def show_notification(self, title, message):
        """Show system notification"""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except:
                # Notifications not supported on this system
                pass
    
    def get_autostart_status(self, item):
        """Check if autostart is currently enabled (for menu checkmark)"""
        return self.config.get("autostart", False) if self.config else False
    
    def get_watchdog_status(self, item):
        """Check if watchdog is currently enabled (for menu checkmark)"""
        return self.config.get("use_watchdog", True) if self.config else False
    
    def get_theme_status(self, item):
        """Get current theme for display"""
        return self.config.get("theme", "dark") if self.config else "dark"
    
    def create_menu(self):
        """Create the context menu for the tray icon"""
        theme = self.config.get("theme", "dark") if self.config else "dark"
        
        return pystray.Menu(
            item('📱 Show Main Window', self.show_main_window),
            item('▶️ Manual Sync', self.run_sync),
            pystray.Menu.SEPARATOR,
            item('📂 Open PC Folder', self.open_folder),
            item('📋 Show Logs', self.show_logs),
            item('📊 Statistics', self.show_stats),
            pystray.Menu.SEPARATOR,
            item(f'🎨 Theme: {theme.title()}', self.toggle_theme),
            item('⚙️ Settings', self.open_settings),
            item('🚀 Autostart', self.toggle_autostart, checked=self.get_autostart_status),
            pystray.Menu.SEPARATOR,
            item('❌ Quit', self.quit_app)
        )
    
    def update_menu(self):
        """Update the tray menu (useful after config changes)"""
        if self.icon:
            self.icon.menu = self.create_menu()
    
    def run(self):
        """Start the system tray icon"""
        theme = self.config.get("theme", "dark") if self.config else "dark"
        image = self.create_icon(theme)
        menu = self.create_menu()
        
        self.icon = pystray.Icon(
            "PlaylistConverter",
            image,
            "PlaylistConverter - Playlist Sync Tool",
            menu
        )
        
        log("🖥️ System tray started")
        
        # Show startup notification
        self.show_notification(
            "PlaylistConverter Started", 
            "Right-click icon for options"
        )
        
        # Start the tray (this blocks)
        self.icon.run()

class TrayManager:
    """Manager class for easier tray integration"""
    def __init__(self, profile="default"):
        self.profile = profile
        self.tray = None
        self.watchdog_observer = None
        
    def start_with_watchdog(self, cfg, config, **kwargs):
        """Start tray with watchdog running in background"""
        # Start watchdog in background thread if enabled
        if config.get("use_watchdog", True):
            def watchdog_thread():
                try:
                    from main import launch_main
                    launch_main(cfg, config, **kwargs)
                except Exception as e:
                    log(f"🚨 Watchdog thread error: {e}")
            
            threading.Thread(target=watchdog_thread, daemon=True).start()
        
        # Start tray (this blocks)
        self.tray = PlaylistConverterTray(self.profile)
        self.tray.run()
    
    def start_tray_only(self):
        """Start tray without watchdog"""
        self.tray = PlaylistConverterTray(self.profile)
        self.tray.run()

def start_tray(profile="default"):
    """Entry point to start the system tray"""
    tray = PlaylistConverterTray(profile)
    tray.run()

def start_tray_with_watchdog(cfg, config, profile="default", **kwargs):
    """Start tray with watchdog support"""
    manager = TrayManager(profile)
    manager.start_with_watchdog(cfg, config, **kwargs)

if __name__ == "__main__":
    start_tray()=sync_thread, daemon=True.start()
    
    def show_main_window(self, icon=None, item=None):
        """Show the main application window"""
        def launch_window():
            try:
                if not self.main_window or not self.main_window.root or not self.main_window.root.winfo_exists():
                    self.main_window = None
                    launch_main_gui(self.profile)
                else:
                    # Bring existing window to front
                    self.main_window.root.lift()
                    self.main_window.root.attributes('-topmost', True)
                    self.main_window.root.attributes('-topmost', False)
            except Exception as e:
                log(f"🚨 Failed to show main window: {e}")
        
        threading.Thread(target)