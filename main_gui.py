# main_gui.py - Enhanced main GUI with conflict management
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
from config import load_config, save_config
from conversion import detect_and_handle_conflicts, scan_all_playlists_for_duplicates  # Fixed import
from conversion import SyncConfig, folders
from conflict_resolution_gui import launch_conflict_gui  # Fixed import

class PlaylistConverterMainGUI:
    """Enhanced main GUI with conflict management features"""
    
    def __init__(self, profile="default"):
        self.profile = profile
        self.config = load_config(profile)
        self.theme_name = self.config.get("theme", "dark") if self.config else "dark"
        self.setup_theme()
        
        if self.config:
            folders["pc"] = self.config["pc_folder"]
            folders["smartphone"] = self.config["smartphone_folder"]
            
            self.cfg = SyncConfig(
                delay=self.config["process_delay"],
                block_duration=self.config["block_duration"],
                max_backups=self.config["max_backups"]
            )
        else:
            self.cfg = None
        
        self.root = None
        self.status_var = None
        self.log_text = None
        self.stats_labels = {}
        self.conflict_indicator = None
        self.duplicate_indicator = None
        
    def setup_theme(self):
        """Setup theme colors"""
        if self.theme_name == "dark":
            self.theme = {
                "bg": "#2b2b2b",
                "fg": "#ffffff",
                "button_bg": "#404040",
                "button_fg": "#ffffff",
                "entry_bg": "#404040",
                "entry_fg": "#ffffff",
                "frame_bg": "#2b2b2b",
                "accent": "#0078d4",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545"
            }
        else:
            self.theme = {
                "bg": "#ffffff",
                "fg": "#000000",
                "button_bg": "#e1e1e1",
                "button_fg": "#000000",
                "entry_bg": "#ffffff",
                "entry_fg": "#000000",
                "frame_bg": "#f0f0f0",
                "accent": "#0078d4",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545"
            }
    
    def apply_theme(self, widget, widget_type="default"):
        """Apply theme to widget"""
        try:
            if widget_type == "button":
                widget.config(
                    bg=self.theme["button_bg"],
                    fg=self.theme["button_fg"],
                    activebackground=self.theme["accent"],
                    activeforeground="#ffffff"
                )
            elif widget_type == "entry":
                widget.config(
                    bg=self.theme["entry_bg"],
                    fg=self.theme["entry_fg"],
                    insertbackground=self.theme["entry_fg"]
                )
            elif widget_type == "text":
                widget.config(
                    bg=self.theme["entry_bg"],
                    fg=self.theme["entry_fg"],
                    insertbackground=self.theme["entry_fg"]
                )
            elif widget_type == "frame":
                widget.config(bg=self.theme["frame_bg"])
            else:
                widget.config(bg=self.theme["bg"], fg=self.theme["fg"])
        except tk.TclError:
            pass
    
    def launch(self):
        """Launch the main GUI"""
        if not self.config:
            messagebox.showerror("No Configuration", "Please run setup first")
            return
        
        self.root = tk.Tk()
        self.root.title("PlaylistConverter")
        self.root.geometry("900x650")
        self.apply_theme(self.root)
        
        self.create_main_window()
        self.update_status()
        
        # Start periodic checks
        self.root.after(5000, self.periodic_check)
        self.root.mainloop()
    
    def create_main_window(self):
        """Create the main window layout"""
        # Title bar
        title_frame = tk.Frame(self.root)
        self.apply_theme(title_frame, "frame")
        title_frame.pack(fill="x", padx=10, pady=5)
        
        title = tk.Label(title_frame, text="🎧 PlaylistConverter", font=("Arial", 16, "bold"))
        self.apply_theme(title)
        title.pack(side="left")
        
        # Status indicators
        indicators_frame = tk.Frame(title_frame)
        self.apply_theme(indicators_frame, "frame")
        indicators_frame.pack(side="right")
        
        self.conflict_indicator = tk.Label(indicators_frame, text="⚔️", font=("Arial", 12))
        self.conflict_indicator.pack(side="right", padx=5)
        
        self.duplicate_indicator = tk.Label(indicators_frame, text="🔍", font=("Arial", 12))  
        self.duplicate_indicator.pack(side="right", padx=5)
        
        # Status frame
        status_frame = tk.LabelFrame(self.root, text="Status", font=("Arial", 10, "bold"))
        self.apply_theme(status_frame, "frame")
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = tk.Label(status_frame, textvariable=self.status_var)
        self.apply_theme(status_label)
        status_label.pack(pady=5)
        
        # Quick actions frame
        actions_frame = tk.LabelFrame(self.root, text="Quick Actions", font=("Arial", 10, "bold"))
        self.apply_theme(actions_frame, "frame")
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        # First row of buttons
        buttons_frame1 = tk.Frame(actions_frame)
        self.apply_theme(buttons_frame1, "frame")
        buttons_frame1.pack(fill="x", padx=5, pady=5)
        
        sync_btn = tk.Button(buttons_frame1, text="🔄 Manual Sync", 
                           command=self.manual_sync, width=15, font=("Arial", 9, "bold"))
        self.apply_theme(sync_btn, "button")
        sync_btn.pack(side="left", padx=2)
        
        conflicts_btn = tk.Button(buttons_frame1, text="⚔️ Manage Conflicts",
                                command=self.open_conflict_manager, width=15, font=("Arial", 9, "bold"))
        self.apply_theme(conflicts_btn, "button")
        conflicts_btn.pack(side="left", padx=2)
        
        duplicates_btn = tk.Button(buttons_frame1, text="🔍 Find Duplicates", 
                                 command=self.quick_duplicate_scan, width=15, font=("Arial", 9, "bold"))
        self.apply_theme(duplicates_btn, "button")
        duplicates_btn.pack(side="left", padx=2)
        
        # Second row of buttons
        buttons_frame2 = tk.Frame(actions_frame)
        self.apply_theme(buttons_frame2, "frame")
        buttons_frame2.pack(fill="x", padx=5, pady=5)
        
        settings_btn = tk.Button(buttons_frame2, text="⚙️ Settings", 
                               command=self.open_settings, width=15, font=("Arial", 9))
        self.apply_theme(settings_btn, "button")
        settings_btn.pack(side="left", padx=2)
        
        pc_folder_btn = tk.Button(buttons_frame2, text="📂 Open PC Folder",
                                command=self.open_pc_folder, width=15, font=("Arial", 9))
        self.apply_theme(pc_folder_btn, "button")
        pc_folder_btn.pack(side="left", padx=2)
        
        logs_btn = tk.Button(buttons_frame2, text="📋 View Logs",
                           command=self.view_logs, width=15, font=("Arial", 9))
        self.apply_theme(logs_btn, "button")
        logs_btn.pack(side="left", padx=2)
        
        # Stats frame
        stats_frame = tk.LabelFrame(self.root, text="Statistics", font=("Arial", 10, "bold"))
        self.apply_theme(stats_frame, "frame")
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Create stats display
        stats_grid = tk.Frame(stats_frame)
        self.apply_theme(stats_grid, "frame")
        stats_grid.pack(fill="x", padx=10, pady=10)
        
        stats_info = [
            ("Files Synced", "files_synced"),
            ("Last Sync", "last_sync"),
            ("Conflicts Found", "conflicts"),
            ("Duplicates Found", "duplicates"),
            ("Uptime", "uptime"),
            ("Errors", "errors")
        ]
        
        for i, (label_text, key) in enumerate(stats_info):
            row = i // 3
            col = i % 3
            
            stat_frame = tk.Frame(stats_grid)
            self.apply_theme(stat_frame, "frame")
            stat_frame.grid(row=row, column=col, sticky="w", padx=20, pady=5)
            
            label = tk.Label(stat_frame, text=f"{label_text}:", font=("Arial", 9, "bold"))
            self.apply_theme(label)
            label.pack(side="left")
            
            value_label = tk.Label(stat_frame, text="0", font=("Arial", 9))
            self.apply_theme(value_label)
            value_label.pack(side="left", padx=(5, 0))
            
            self.stats_labels[key] = value_label
        
        # Activity log frame
        log_frame = tk.LabelFrame(self.root, text="Recent Activity", font=("Arial", 10, "bold"))
        self.apply_theme(log_frame, "frame")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Log text with scrollbar
        log_container = tk.Frame(log_frame)
        self.apply_theme(log_container, "frame")
        log_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_container, height=12, wrap="word", font=("Consolas", 9))
        log_scrollbar = tk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        self.apply_theme(self.log_text, "text")
        
        # Theme selector at bottom
        theme_frame = tk.Frame(self.root)
        self.apply_theme(theme_frame, "frame")
        theme_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        tk.Label(theme_frame, text="Theme:").pack(side="right", padx=(0, 5))
        self.apply_theme(theme_frame.children["!label"])
        
        theme_var = tk.StringVar(value=self.theme_name)
        theme_combo = ttk.Combobox(theme_frame, textvariable=theme_var,
                                 values=["dark", "light"], state="readonly", width=10)
        theme_combo.pack(side="right")
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.change_theme(theme_var.get()))
    
    def change_theme(self, new_theme):
        """Change theme and update display"""
        self.theme_name = new_theme
        self.setup_theme()
        
        # Save to config
        if self.config:
            self.config["theme"] = new_theme
            save_config(self.config, self.profile)
        
        # Reapply theme to all widgets
        self.apply_theme_recursive(self.root)
    
    def apply_theme_recursive(self, widget):
        """Recursively apply theme"""
        widget_class = widget.winfo_class()
        
        if widget_class == "Button":
            self.apply_theme(widget, "button")
        elif widget_class == "Entry":
            self.apply_theme(widget, "entry")
        elif widget_class == "Text":
            self.apply_theme(widget, "text")
        elif widget_class in ["Frame", "LabelFrame"]:
            self.apply_theme(widget, "frame")
        elif widget_class in ["Label"]:
            self.apply_theme(widget)
        elif widget_class in ["Toplevel", "Tk"]:
            self.apply_theme(widget)
        
        for child in widget.winfo_children():
            self.apply_theme_recursive(child)
    
    def manual_sync(self):
        """Trigger manual sync"""
        def sync_thread():
            try:
                from conversion import initial_sync_with_comparison  # Fixed import
                
                self.add_log("🔄 Manual sync started...")
                self.update_status_indicator("Syncing...")
                
                initial_sync_with_comparison(self.cfg, verbose=True)
                
                self.add_log("✅ Manual sync completed")
                self.update_status_indicator("✅ Ready")
                
                # Update stats
                self.stats_labels["files_synced"].config(text=str(int(self.stats_labels["files_synced"]["text"]) + 1))
                self.stats_labels["last_sync"].config(text=datetime.now().strftime("%H:%M:%S"))
                
            except Exception as e:
                self.add_log(f"🚨 Manual sync failed: {e}")
                self.update_status_indicator("❌ Error")
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def open_conflict_manager(self):
        """Open the conflict management GUI"""
        try:
            launch_conflict_gui(self.config, self.theme_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open conflict manager: {e}")
    
    def quick_duplicate_scan(self):
        """Quick scan for duplicates"""
        def scan_thread():
            try:
                self.add_log("🔍 Scanning for duplicates...")
                self.update_status_indicator("Scanning...")
                
                total_duplicates = scan_all_playlists_for_duplicates(self.cfg, verbose=False)
                
                self.add_log(f"📊 Found {total_duplicates} duplicates total")
                self.stats_labels["duplicates"].config(text=str(total_duplicates))
                
                if total_duplicates > 0:
                    self.update_duplicate_indicator(total_duplicates, "warning")
                    
                    # Ask user if they want to open the full manager
                    self.root.after(0, lambda: self.prompt_open_duplicate_manager(total_duplicates))
                else:
                    self.update_duplicate_indicator(0, "success")
                    self.root.after(0, lambda: messagebox.showinfo("No Duplicates", "No duplicates found!"))
                
                self.update_status_indicator("✅ Ready")
                
            except Exception as e:
                self.add_log(f"🚨 Duplicate scan failed: {e}")
                self.update_status_indicator("❌ Error")
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def prompt_open_duplicate_manager(self, duplicate_count):
        """Prompt user to open the full duplicate manager"""
        result = messagebox.askyesno(
            "Duplicates Found",
            f"Found {duplicate_count} duplicates in your playlists.\n\n"
            f"Would you like to open the Conflict Manager to review and remove them?"
        )
        
        if result:
            self.open_conflict_manager()
    
    def periodic_check(self):
        """Periodic check for conflicts and duplicates"""
        def check_thread():
            try:
                # Quick conflict check
                conflicts = detect_and_handle_conflicts(self.cfg, verbose=False)
                conflict_count = len(conflicts) if conflicts else 0
                
                # Update conflict indicator
                self.root.after(0, lambda: self.update_conflict_indicator(conflict_count))
                self.root.after(0, lambda: self.stats_labels["conflicts"].config(text=str(conflict_count)))
                
            except:
                pass  # Ignore errors in background checks
        
        threading.Thread(target=check_thread, daemon=True).start()
        
        # Schedule next check
        self.root.after(30000, self.periodic_check)  # Check every 30 seconds
    
    def update_conflict_indicator(self, count, status_type="default"):
        """Update the conflict indicator"""
        if count == 0:
            color = self.theme["success"]
            tooltip = "No conflicts detected"
        else:
            color = self.theme["danger"] 
            tooltip = f"{count} conflicts found"
        
        self.conflict_indicator.config(fg=color)
        # In a full implementation, you'd add tooltip functionality here
    
    def update_duplicate_indicator(self, count, status_type="default"):
        """Update the duplicate indicator"""
        if count == 0:
            color = self.theme["success"]
        elif status_type == "warning":
            color = self.theme["warning"]
        else:
            color = self.theme["danger"]
        
        self.duplicate_indicator.config(fg=color)
    
    def update_status_indicator(self, status):
        """Update the main status"""
        if self.status_var:
            self.status_var.set(status)
    
    def add_log(self, message):
        """Add message to activity log"""
        if self.log_text:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            
            # Keep only last 100 lines
            lines = self.log_text.get("1.0", tk.END).split("\n")
            if len(lines) > 100:
                self.log_text.delete("1.0", f"{len(lines)-100}.0")
    
    def open_settings(self):
        """Open settings window"""
        messagebox.showinfo("Settings", "Settings window would open here")
    
    def open_pc_folder(self):
        """Open PC folder"""
        if self.config and self.config.get("pc_folder"):
            import subprocess, sys, os
            folder_path = self.config["pc_folder"]
            
            try:
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_path])
                else:
                    subprocess.Popen(["xdg-open", folder_path])
                self.add_log(f"📂 Opened PC folder: {folder_path}")
            except Exception as e:
                self.add_log(f"🚨 Failed to open folder: {e}")
    
    def view_logs(self):
        """Open logs folder"""
        try:
            logs_path = folders["logs"]
            if os.path.exists(logs_path):
                import subprocess, sys, os
                if sys.platform == "win32":
                    os.startfile(logs_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", logs_path])
                else:
                    subprocess.Popen(["xdg-open", logs_path])
                self.add_log(f"📋 Opened logs folder: {logs_path}")
            else:
                self.add_log("⚠️ Logs folder doesn't exist yet")
        except Exception as e:
            self.add_log(f"🚨 Failed to open logs: {e}")
    
    def update_status(self):
        """Update status display"""
        if self.config:
            if self.config.get("use_watchdog", True):
                status = "🟢 Real-time sync active"
            else:
                status = "🟡 Scheduled sync only"
        else:
            status = "🔴 Not configured"
        
        self.update_status_indicator(status)

# Entry function to launch the enhanced main GUI
def launch_enhanced_main_gui(profile="default"):
    """Launch the enhanced main GUI with conflict management"""
    gui = PlaylistConverterMainGUI(profile)
    gui.launch()

if __name__ == "__main__":
    launch_enhanced_main_gui()