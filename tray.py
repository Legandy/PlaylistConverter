# tray.py - System Tray Implementation for PlaylistConverter
import threading
import os
import sys
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from config import load_config, apply_autostart_setting
from conversion import initial_sync_with_comparison, SyncConfig, folders, log
from gui import launch_gui
import webbrowser

class PlaylistConverterTray:
    def __init__(self, profile="default"):
        self.profile = profile
        self.config = load_config(profile)
        self.icon = None
        self.setup_folders()
    
    def setup_folders(self):
        """Initialize folder paths from config"""
        if self.config:
            folders["pc"] = self.config["pc_folder"]
            folders["smartphone"] = self.config["smartphone_folder"]
    
    def create_icon(self):
        """Create a simple icon if playlist_icon.ico doesn't exist"""
        try:
            # Try to load existing icon
            icon_path = os.path.join(os.path.dirname(__file__), "playlist_icon.ico")
            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except:
            pass
        
        # Create a simple fallback icon
        width = height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a simple music note-like shape
        draw.ellipse([16, 40, 32, 56], fill=(0, 120, 200, 255))
        draw.rectangle([28, 16, 32, 48], fill=(0, 120, 200, 255))
        draw.ellipse([24, 12, 40, 28], fill=(0, 120, 200, 255))
        
        return image
    
    def run_sync(self, icon=None, item=None):
        """Manually trigger sync operation"""
        def sync_thread():
            try:
                if not self.config:
                    log("⚠️ No configuration found. Please run setup first.")
                    return
                
                cfg = SyncConfig(
                    delay=self.config["process_delay"],
                    block_duration=self.config["block_duration"],
                    max_backups=self.config["max_backups"]
                )
                
                log("🔄 Manual sync triggered from tray")
                initial_sync_with_comparison(cfg)
                log("✅ Manual sync completed")
                
            except Exception as e:
                log(f"🚨 Manual sync failed: {e}")
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def open_folder(self, icon=None, item=None):
        """Open the base playlist folder in file explorer"""
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
            else:
                log("⚠️ No PC folder configured")
        except Exception as e:
            log(f"🚨 Failed to open folder: {e}")
    
    def toggle_autostart(self, icon=None, item=None):
        """Toggle autostart setting"""
        try:
            if not self.config:
                log("⚠️ No configuration found")
                return
            
            current_autostart = self.config.get("autostart", False)
            new_autostart = not current_autostart
            
            apply_autostart_setting(new_autostart)
            
            # Update config
            self.config["autostart"] = new_autostart
            from config import save_config
            save_config(self.config, self.profile)
            
            status = "enabled" if new_autostart else "disabled"
            log(f"⚙️ Autostart {status}")
            
        except Exception as e:
            log(f"🚨 Failed to toggle autostart: {e}")
    
    def reset_setup(self, icon=None, item=None):
        """Launch the setup GUI to reconfigure"""
        def setup_callback(data, profile_name):
            from config import save_config
            save_config(data, profile_name)
            self.config = data
            self.setup_folders()
            log("💾 Configuration updated from tray")
        
        try:
            launch_gui(
                save_callback=setup_callback,
                autostart_callback=apply_autostart_setting,
                profile=self.profile
            )
        except Exception as e:
            log(f"🚨 Failed to launch setup: {e}")
    
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
        except Exception as e:
            log(f"🚨 Failed to open logs: {e}")
    
    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        log("👋 PlaylistConverter shutting down")
        if self.icon:
            self.icon.stop()
    
    def get_autostart_status(self, item):
        """Check if autostart is currently enabled (for menu checkmark)"""
        return self.config.get("autostart", False) if self.config else False
    
    def create_menu(self):
        """Create the context menu for the tray icon"""
        return pystray.Menu(
            item('▶️ Run Sync', self.run_sync),
            item('📂 Open PC Folder', self.open_folder),
            item('📋 Show Logs', self.show_logs),
            pystray.Menu.SEPARATOR,
            item('⚙️ Autostart', self.toggle_autostart, checked=self.get_autostart_status),
            item('🔄 Reset Setup', self.reset_setup),
            pystray.Menu.SEPARATOR,
            item('❌ Quit', self.quit_app)
        )
    
    def run(self):
        """Start the system tray icon"""
        image = self.create_icon()
        menu = self.create_menu()
        
        self.icon = pystray.Icon(
            "PlaylistConverter",
            image,
            "PlaylistConverter - Playlist Sync Tool",
            menu
        )
        
        log("🖥️ System tray started")
        self.icon.run()

def start_tray(profile="default"):
    """Entry point to start the system tray"""
    tray = PlaylistConverterTray(profile)
    tray.run()

if __name__ == "__main__":
    start_tray()