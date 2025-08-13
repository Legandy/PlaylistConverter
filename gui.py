import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time
from datetime import datetime
from config import save_config, load_config, validate_config

# Theme configurations
THEMES = {
    "dark": {
        "bg": "#2b2b2b",
        "fg": "#ffffff",
        "select_bg": "#404040",
        "select_fg": "#ffffff",
        "button_bg": "#404040",
        "button_fg": "#ffffff",
        "entry_bg": "#404040",
        "entry_fg": "#ffffff",
        "frame_bg": "#2b2b2b",
        "accent": "#0078d4"
    },
    "light": {
        "bg": "#ffffff",
        "fg": "#000000", 
        "select_bg": "#e1e1e1",
        "select_fg": "#000000",
        "button_bg": "#e1e1e1",
        "button_fg": "#000000",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "frame_bg": "#f0f0f0",
        "accent": "#0078d4"
    }
}

# Available options for scheduled sync intervals
SCHEDULE_OPTIONS = [
    "Never",
    "Every 15 min", 
    "Every 30 min",
    "Hourly",
    "Daily @ 02:00"
]

class ThemedWidget:
    """Base class for applying themes to widgets"""
    def __init__(self, theme_name="dark"):
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
    
    def apply_theme(self, widget, widget_type="default"):
        """Apply theme to a widget"""
        try:
            if widget_type == "button":
                widget.config(
                    bg=self.theme["button_bg"],
                    fg=self.theme["button_fg"],
                    activebackground=self.theme["select_bg"],
                    activeforeground=self.theme["select_fg"],
                    relief="flat",
                    borderwidth=1
                )
            elif widget_type == "entry":
                widget.config(
                    bg=self.theme["entry_bg"],
                    fg=self.theme["entry_fg"],
                    insertbackground=self.theme["fg"],
                    selectbackground=self.theme["accent"],
                    relief="solid",
                    borderwidth=1
                )
            elif widget_type == "text":
                widget.config(
                    bg=self.theme["entry_bg"],
                    fg=self.theme["entry_fg"],
                    insertbackground=self.theme["fg"],
                    selectbackground=self.theme["accent"],
                    relief="solid",
                    borderwidth=1
                )
            elif widget_type == "frame":
                widget.config(
                    bg=self.theme["frame_bg"]
                )
            else:  # default (labels, root, etc.)
                widget.config(
                    bg=self.theme["bg"],
                    fg=self.theme["fg"]
                )
        except tk.TclError:
            # Some widgets don't support all config options
            pass

class PlaylistConverterSetup(ThemedWidget):
    """Setup/Configuration GUI"""
    def __init__(self, save_callback, autostart_callback, is_dev=False, profile="default", theme="dark"):
        super().__init__(theme)
        self.profile_name = profile
        self.config_data = load_config(profile) or {}
        self.save_callback = save_callback
        self.autostart_callback = autostart_callback
        self.is_dev = is_dev
        
        self.root = None
        self.watchdog_var = None
        self.schedule_var = None
        
    def launch(self):
        """Launch the setup window"""
        self.root = tk.Tk()
        self.root.title("PlaylistConverter Setup")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        self.apply_theme(self.root)
        
        # Theme selector at top
        theme_frame = tk.Frame(self.root)
        self.apply_theme(theme_frame, "frame")
        theme_frame.pack(pady=10, fill="x", padx=20)
        
        tk.Label(theme_frame, text="Theme:").pack(side="left")
        self.apply_theme(theme_frame.children["!label"], "default")
        
        theme_var = tk.StringVar(value=self.theme_name)
        theme_combo = ttk.Combobox(theme_frame, textvariable=theme_var, 
                                 values=["dark", "light"], state="readonly", width=10)
        theme_combo.pack(side="left", padx=(10, 0))
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.change_theme(theme_var.get()))
        
        # Main content
        self.create_main_content()
        
        self.root.mainloop()
    
    def change_theme(self, new_theme):
        """Change the theme and refresh the window"""
        self.theme_name = new_theme
        self.theme = THEMES[new_theme]
        self.config_data["theme"] = new_theme
        
        # Reapply theme to all widgets
        self.apply_theme_recursive(self.root)
    
    def apply_theme_recursive(self, widget):
        """Recursively apply theme to all widgets"""
        widget_class = widget.winfo_class()
        
        if widget_class == "Button":
            self.apply_theme(widget, "button")
        elif widget_class == "Entry":
            self.apply_theme(widget, "entry")
        elif widget_class == "Text":
            self.apply_theme(widget, "text")
        elif widget_class == "Frame":
            self.apply_theme(widget, "frame")
        elif widget_class in ["Label", "Checkbutton"]:
            self.apply_theme(widget, "default")
        elif widget_class in ["Toplevel", "Tk"]:
            self.apply_theme(widget, "default")
            
        # Apply to all children
        for child in widget.winfo_children():
            self.apply_theme_recursive(child)
    
    def create_main_content(self):
        """Create the main setup content"""
        # PC Folder Section
        tk.Label(self.root, text="🎧 PC Playlist Folder:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        self.apply_theme(self.root.children["!label"], "default")
        
        pc_entry = tk.Entry(self.root, width=60, font=("Arial", 9))
        pc_entry.pack(pady=5)
        pc_entry.insert(0, self.config_data.get("pc_folder", ""))
        self.apply_theme(pc_entry, "entry")
        
        pc_btn = tk.Button(self.root, text="Browse...", 
                          command=lambda: self.choose_folder("pc_folder", pc_entry))
        pc_btn.pack(pady=(2, 15))
        self.apply_theme(pc_btn, "button")
        
        # Smartphone Folder Section  
        tk.Label(self.root, text="📱 Smartphone Playlist Folder:", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        self.apply_theme(self.root.children["!label2"], "default")
        
        phone_entry = tk.Entry(self.root, width=60, font=("Arial", 9))
        phone_entry.pack(pady=5)
        phone_entry.insert(0, self.config_data.get("smartphone_folder", ""))
        self.apply_theme(phone_entry, "entry")
        
        phone_btn = tk.Button(self.root, text="Browse...",
                             command=lambda: self.choose_folder("smartphone_folder", phone_entry))
        phone_btn.pack(pady=(2, 20))
        self.apply_theme(phone_btn, "button")
        
        # Options Frame
        options_frame = tk.Frame(self.root)
        self.apply_theme(options_frame, "frame")
        options_frame.pack(pady=10, fill="x", padx=20)
        
        # Watchdog checkbox
        self.watchdog_var = tk.BooleanVar()
        self.watchdog_var.set(self.config_data.get("use_watchdog", True))
        watchdog_cb = tk.Checkbutton(options_frame, text="Enable Real-Time Sync (Watchdog)",
                                   variable=self.watchdog_var, command=self.toggle_watchdog_checkbox)
        watchdog_cb.pack(anchor="w", pady=5)
        self.apply_theme(watchdog_cb, "default")
        
        # Schedule interval
        tk.Label(options_frame, text="⏱️ Scheduled Sync Interval:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 5))
        self.apply_theme(options_frame.children["!label"], "default")
        
        self.schedule_var = tk.StringVar()
        current_schedule = self.config_data.get("schedule_interval", "Never")
        if current_schedule not in SCHEDULE_OPTIONS:
            current_schedule = "Never"
        self.schedule_var.set(current_schedule)
        
        schedule_dropdown = ttk.Combobox(options_frame, textvariable=self.schedule_var,
                                       values=SCHEDULE_OPTIONS, state="readonly")
        schedule_dropdown.pack(anchor="w", pady=5)
        schedule_dropdown.bind("<<ComboboxSelected>>", self.change_schedule_interval)
        
        # Developer Mode (if enabled)
        if self.is_dev:
            dev_var = tk.BooleanVar()
            dev_var.set(self.config_data.get("developer_mode", False))
            
            dev_cb = tk.Checkbutton(options_frame, text="Enable Developer Mode",
                                  variable=dev_var, command=lambda: setattr(self.config_data, "developer_mode", dev_var.get()))
            dev_cb.pack(anchor="w", pady=(15, 0))
            self.apply_theme(dev_cb, "default")
        
        # Save button
        save_btn = tk.Button(self.root, text="💾 Save & Launch", font=("Arial", 10, "bold"),
                           command=lambda: self.save_and_close(pc_entry, phone_entry))
        save_btn.pack(pady=(30, 20))
        self.apply_theme(save_btn, "button")
    
    def choose_folder(self, label_key, entry_widget):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)
            self.config_data[label_key] = folder
    
    def toggle_watchdog_checkbox(self):
        """Toggle watchdog setting"""
        self.config_data["use_watchdog"] = self.watchdog_var.get()
    
    def change_schedule_interval(self, event):
        """Handle schedule interval change"""
        selected = self.schedule_var.get()
        self.config_data["schedule_interval"] = selected
    
    def save_and_close(self, pc_entry, phone_entry):
        """Save configuration and close window"""
        self.config_data["pc_folder"] = pc_entry.get()
        self.config_data["smartphone_folder"] = phone_entry.get()
        
        # Validate configuration
        validation = validate_config(self.config_data)
        if not validation:
            messagebox.showerror("Configuration Error", 
                               "Please check that both folders exist and are accessible.")
            return
        
        self.save_callback(self.config_data, self.profile_name)
        self.autostart_callback(self.config_data.get("autostart", False))
        self.root.destroy()

class PlaylistConverterMain(ThemedWidget):
    """Main application GUI"""
    def __init__(self, profile="default", theme=None):
        # Load theme from config
        config = load_config(profile)
        if not theme and config:
            theme = config.get("theme", "dark")
        super().__init__(theme or "dark")
        
        self.profile = profile
        self.config = config
        self.root = None
        self.status_var = None
        self.log_text = None
        self.stats_labels = {}
        self.running = False
        
    def launch(self):
        """Launch the main application window"""
        if not self.config:
            messagebox.showerror("No Configuration", 
                               "Please run setup first (--setup flag)")
            return
            
        self.root = tk.Tk()
        self.root.title("PlaylistConverter")
        self.root.geometry("700x500")
        self.apply_theme(self.root)
        
        self.create_main_window()
        self.update_status()
        
        # Start update loop
        self.root.after(1000, self.update_loop)
        self.root.mainloop()
    
    def create_main_window(self):
        """Create the main window layout"""
        # Title
        title = tk.Label(self.root, text="🎧 PlaylistConverter", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        self.apply_theme(title, "default")
        
        # Status frame
        status_frame = tk.Frame(self.root)
        self.apply_theme(status_frame, "frame")
        status_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(status_frame, text="Status:", font=("Arial", 10, "bold")).pack(side="left")
        self.apply_theme(status_frame.children["!label"], "default")
        
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = tk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side="left", padx=(10, 0))
        self.apply_theme(status_label, "default")
        
        # Stats frame
        stats_frame = tk.LabelFrame(self.root, text="Statistics", font=("Arial", 10, "bold"))
        self.apply_theme(stats_frame, "frame")
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # Create stats labels
        stats_info = [
            ("Files Synced", "files_synced"),
            ("Last Sync", "last_sync"),
            ("Uptime", "uptime"),
            ("Errors", "errors")
        ]
        
        for i, (label_text, key) in enumerate(stats_info):
            row = i // 2
            col = i % 2
            
            label_frame = tk.Frame(stats_frame)
            self.apply_theme(label_frame, "frame")
            label_frame.grid(row=row, column=col, sticky="w", padx=10, pady=5)
            
            tk.Label(label_frame, text=f"{label_text}:", font=("Arial", 9, "bold")).pack(side="left")
            self.apply_theme(label_frame.children["!label"], "default")
            
            value_label = tk.Label(label_frame, text="0")
            value_label.pack(side="left", padx=(5, 0))
            self.apply_theme(value_label, "default")
            
            self.stats_labels[key] = value_label
        
        # Control buttons frame
        control_frame = tk.Frame(self.root)
        self.apply_theme(control_frame, "frame")
        control_frame.pack(fill="x", padx=20, pady=10)
        
        buttons = [
            ("▶️ Manual Sync", self.manual_sync),
            ("⚙️ Settings", self.open_settings),
            ("📂 Open PC Folder", self.open_pc_folder),
            ("📋 View Logs", self.view_logs)
        ]
        
        for text, command in buttons:
            btn = tk.Button(control_frame, text=text, command=command, width=15)
            btn.pack(side="left", padx=5)
            self.apply_theme(btn, "button")
        
        # Log display
        log_frame = tk.LabelFrame(self.root, text="Recent Activity", font=("Arial", 10, "bold"))
        self.apply_theme(log_frame, "frame")
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scrolled text widget
        text_frame = tk.Frame(log_frame)
        self.apply_theme(text_frame, "frame")
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(text_frame, height=10, wrap="word", font=("Consolas", 9))
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.apply_theme(self.log_text, "text")
        
        # Theme selector
        theme_frame = tk.Frame(self.root)
        self.apply_theme(theme_frame, "frame")
        theme_frame.pack(side="bottom", fill="x", padx=20, pady=5)
        
        tk.Label(theme_frame, text="Theme:").pack(side="right", padx=(0, 5))
        self.apply_theme(theme_frame.children["!label"], "default")
        
        theme_var = tk.StringVar(value=self.theme_name)
        theme_combo = ttk.Combobox(theme_frame, textvariable=theme_var,
                                 values=["dark", "light"], state="readonly", width=10)
        theme_combo.pack(side="right")
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.change_theme(theme_var.get()))
    
    def change_theme(self, new_theme):
        """Change theme and save to config"""
        self.theme_name = new_theme
        self.theme = THEMES[new_theme]
        
        # Save theme to config
        if self.config:
            self.config["theme"] = new_theme
            save_config(self.config, self.profile)
        
        # Apply theme recursively
        self.apply_theme_recursive(self.root)
    
    def apply_theme_recursive(self, widget):
        """Recursively apply theme to all widgets"""
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
            self.apply_theme(widget, "default")
        elif widget_class in ["Toplevel", "Tk"]:
            self.apply_theme(widget, "default")
            
        # Apply to all children
        for child in widget.winfo_children():
            self.apply_theme_recursive(child)
    
    def manual_sync(self):
        """Trigger manual sync"""
        def sync_thread():
            try:
                from conversion import initial_sync_with_comparison, SyncConfig
                
                cfg = SyncConfig(
                    delay=self.config["process_delay"],
                    block_duration=self.config["block_duration"],
                    max_backups=self.config["max_backups"]
                )
                
                self.add_log("🔄 Manual sync started...")
                initial_sync_with_comparison(cfg)
                self.add_log("✅ Manual sync completed")
                
            except Exception as e:
                self.add_log(f"🚨 Manual sync failed: {e}")
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def open_settings(self):
        """Open settings window"""
        def save_callback(data, profile_name):
            save_config(data, profile_name)
            self.config = data
        
        setup = PlaylistConverterSetup(
            save_callback=save_callback,
            autostart_callback=lambda x: None,
            profile=self.profile,
            theme=self.theme_name
        )
        setup.launch()
    
    def open_pc_folder(self):
        """Open PC playlist folder"""
        if self.config and self.config.get("pc_folder"):
            import subprocess, sys
            folder_path = self.config["pc_folder"]
            
            try:
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_path])
                else:
                    subprocess.Popen(["xdg-open", folder_path])
                self.add_log(f"📂 Opened folder: {folder_path}")
            except Exception as e:
                self.add_log(f"🚨 Failed to open folder: {e}")
    
    def view_logs(self):
        """Open logs folder"""
        try:
            from conversion import folders
            logs_path = folders["logs"]
            
            if os.path.exists(logs_path):
                import subprocess, sys
                if sys.platform == "win32":
                    os.startfile(logs_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", logs_path])
                else:
                    subprocess.Popen(["xdg-open", logs_path])
                self.add_log(f"📋 Opened logs: {logs_path}")
            else:
                self.add_log("⚠️ Logs folder doesn't exist yet")
        except Exception as e:
            self.add_log(f"🚨 Failed to open logs: {e}")
    
    def add_log(self, message):
        """Add message to log display"""
        if self.log_text:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            
            # Keep only last 100 lines
            lines = self.log_text.get("1.0", tk.END).split("\n")
            if len(lines) > 100:
                self.log_text.delete("1.0", f"{len(lines)-100}.0")
    
    def update_status(self):
        """Update status display"""
        if self.config:
            if self.config.get("use_watchdog", True):
                status = "🟢 Real-time sync active"
            else:
                status = "🟡 Scheduled sync only"
        else:
            status = "🔴 Not configured"
        
        if self.status_var:
            self.status_var.set(status)
    
    def update_loop(self):
        """Regular update loop"""
        try:
            # Update stats (mock data for now)
            if hasattr(self, 'stats_labels'):
                self.stats_labels.get("files_synced", tk.Label()).config(text="0")
                self.stats_labels.get("last_sync", tk.Label()).config(text="Never")
                self.stats_labels.get("uptime", tk.Label()).config(text="0m")
                self.stats_labels.get("errors", tk.Label()).config(text="0")
            
            # Schedule next update
            if self.root:
                self.root.after(5000, self.update_loop)
        except:
            pass

# Entry functions for the new GUI
def launch_setup_gui(save_callback, autostart_callback, is_dev=False, profile="default"):
    """Launch the setup GUI"""
    config = load_config(profile)
    theme = config.get("theme", "dark") if config else "dark"
    
    setup = PlaylistConverterSetup(
        save_callback=save_callback,
        autostart_callback=autostart_callback,
        is_dev=is_dev,
        profile=profile,
        theme=theme
    )
    setup.launch()

def launch_main_gui(profile="default"):
    """Launch the main application GUI"""
    main_app = PlaylistConverterMain(profile=profile)
    main_app.launch()

# Backward compatibility with existing gui.py
def launch_gui(save_callback, autostart_callback, is_dev=False, profile="default"):
    """Backward compatibility function"""
    launch_setup_gui(save_callback, autostart_callback, is_dev, profile)