# conflict_resolution_gui.py - GUI for conflict resolution and duplicate management
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from conflict_resolution_system import ConflictResolver, ConflictResolution  # Fixed import
from conversion import detect_and_handle_conflicts, scan_all_playlists_for_duplicates, remove_duplicates_from_playlist  # Fixed imports
from conversion import SyncConfig, folders
from config import load_config
import os

class ConflictResolutionGUI:
    """GUI for managing playlist conflicts and duplicates"""
    
    def __init__(self, config=None, theme="dark"):
        self.config = config or load_config()
        self.theme_name = theme
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
        
        self.resolver = ConflictResolver()
        self.root = None
        self.conflicts = []
        self.duplicate_stats = {}
        
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
                "listbox_bg": "#404040",
                "listbox_fg": "#ffffff",
                "accent": "#0078d4"
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
                "listbox_bg": "#ffffff",
                "listbox_fg": "#000000",
                "accent": "#0078d4"
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
                    insertbackground=self.theme["entry_fg"],
                    selectbackground=self.theme["accent"]
                )
            elif widget_type == "listbox":
                widget.config(
                    bg=self.theme["listbox_bg"],
                    fg=self.theme["listbox_fg"],
                    selectbackground=self.theme["accent"],
                    selectforeground="#ffffff"
                )
            elif widget_type == "frame":
                widget.config(bg=self.theme["frame_bg"])
            else:  # labels, root
                widget.config(bg=self.theme["bg"], fg=self.theme["fg"])
        except tk.TclError:
            pass
    
    def launch(self):
        """Launch the conflict resolution GUI"""
        if not self.config:
            messagebox.showerror("No Configuration", "Please configure PlaylistConverter first")
            return
        
        self.root = tk.Tk()
        self.root.title("PlaylistConverter - Conflict Resolution")
        self.root.geometry("800x600")
        self.apply_theme(self.root)
        
        self.create_main_interface()
        self.root.mainloop()
    
    def create_main_interface(self):
        """Create the main interface"""
        # Title
        title_frame = tk.Frame(self.root)
        self.apply_theme(title_frame, "frame")
        title_frame.pack(fill="x", padx=10, pady=10)
        
        title = tk.Label(title_frame, text="🔧 Conflict Resolution & Duplicate Management",
                        font=("Arial", 14, "bold"))
        self.apply_theme(title)
        title.pack()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Conflicts tab
        conflicts_frame = tk.Frame(notebook)
        self.apply_theme(conflicts_frame, "frame")
        notebook.add(conflicts_frame, text="⚔️ Conflicts")
        self.create_conflicts_tab(conflicts_frame)
        
        # Duplicates tab
        duplicates_frame = tk.Frame(notebook)
        self.apply_theme(duplicates_frame, "frame")
        notebook.add(duplicates_frame, text="🔍 Duplicates")
        self.create_duplicates_tab(duplicates_frame)
        
        # Settings tab
        settings_frame = tk.Frame(notebook)
        self.apply_theme(settings_frame, "frame")
        notebook.add(settings_frame, text="⚙️ Settings")
        self.create_settings_tab(settings_frame)
    
    def create_conflicts_tab(self, parent):
        """Create the conflicts management tab"""
        # Scan button
        scan_frame = tk.Frame(parent)
        self.apply_theme(scan_frame, "frame")
        scan_frame.pack(fill="x", padx=10, pady=10)
        
        scan_btn = tk.Button(scan_frame, text="🔍 Scan for Conflicts",
                           command=self.scan_for_conflicts, font=("Arial", 10, "bold"))
        self.apply_theme(scan_btn, "button")
        scan_btn.pack(side="left", padx=(0, 10))
        
        self.conflict_status = tk.Label(scan_frame, text="No scan performed")
        self.apply_theme(self.conflict_status)
        self.conflict_status.pack(side="left")
        
        # Conflicts list
        list_frame = tk.Frame(parent)
        self.apply_theme(list_frame, "frame")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        tk.Label(list_frame, text="Detected Conflicts:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.apply_theme(list_frame.children["!label"])
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_frame)
        self.apply_theme(listbox_frame, "frame")
        listbox_frame.pack(fill="both", expand=True, pady=5)
        
        self.conflicts_listbox = tk.Listbox(listbox_frame)
        self.apply_theme(self.conflicts_listbox, "listbox")
        
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        self.conflicts_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.conflicts_listbox.yview)
        
        self.conflicts_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.conflicts_listbox.bind("<<ListboxSelect>>", self.on_conflict_select)
        
        # Conflict details
        details_frame = tk.Frame(parent)
        self.apply_theme(details_frame, "frame")
        details_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        tk.Label(details_frame, text="Conflict Details:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.apply_theme(details_frame.children["!label"])
        
        self.conflict_details = scrolledtext.ScrolledText(details_frame, height=8, wrap="word")
        self.apply_theme(self.conflict_details, "text")
        self.conflict_details.pack(fill="both", expand=True, pady=5)
        
        # Resolution buttons
        resolution_frame = tk.Frame(parent)
        self.apply_theme(resolution_frame, "frame")
        resolution_frame.pack(fill="x", padx=10, pady=10)
        
        resolve_buttons = [
            ("🏆 PC Wins", ConflictResolution.PC_WINS),
            ("📱 Phone Wins", ConflictResolution.SMARTPHONE_WINS),
            ("🔀 Merge (Keep Dupes)", ConflictResolution.MERGE_BOTH),
            ("🔀 Merge (No Dupes)", ConflictResolution.MERGE_NO_DUPLICATES)
        ]
        
        for text, resolution in resolve_buttons:
            btn = tk.Button(resolution_frame, text=text,
                          command=lambda r=resolution: self.resolve_selected_conflict(r))
            self.apply_theme(btn, "button")
            btn.pack(side="left", padx=5)
    
    def create_duplicates_tab(self, parent):
        """Create the duplicates management tab"""
        # Scan button
        scan_frame = tk.Frame(parent)
        self.apply_theme(scan_frame, "frame")
        scan_frame.pack(fill="x", padx=10, pady=10)
        
        scan_dupes_btn = tk.Button(scan_frame, text="🔍 Scan for Duplicates",
                                 command=self.scan_for_duplicates, font=("Arial", 10, "bold"))
        self.apply_theme(scan_dupes_btn, "button")
        scan_dupes_btn.pack(side="left", padx=(0, 10))
        
        remove_all_btn = tk.Button(scan_frame, text="🧹 Remove All Duplicates",
                                 command=self.remove_all_duplicates, font=("Arial", 10, "bold"))
        self.apply_theme(remove_all_btn, "button")
        remove_all_btn.pack(side="left", padx=5)
        
        self.duplicate_status = tk.Label(scan_frame, text="No scan performed")
        self.apply_theme(self.duplicate_status)
        self.duplicate_status.pack(side="left", padx=(10, 0))
        
        # Results display
        results_frame = tk.Frame(parent)
        self.apply_theme(results_frame, "frame")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        tk.Label(results_frame, text="Duplicate Analysis:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.apply_theme(results_frame.children["!label"])
        
        self.duplicates_text = scrolledtext.ScrolledText(results_frame, wrap="word")
        self.apply_theme(self.duplicates_text, "text")
        self.duplicates_text.pack(fill="both", expand=True, pady=5)
    
    def create_settings_tab(self, parent):
        """Create the settings tab"""
        settings_frame = tk.LabelFrame(parent, text="Default Conflict Resolution", 
                                     font=("Arial", 10, "bold"))
        self.apply_theme(settings_frame, "frame")
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        self.default_resolution = tk.StringVar(value=ConflictResolution.MERGE_NO_DUPLICATES.value)
        
        for resolution in ConflictResolution:
            rb = tk.Radiobutton(settings_frame, text=resolution.value.replace("_", " ").title(),
                              variable=self.default_resolution, value=resolution.value)
            self.apply_theme(rb)
            rb.pack(anchor="w", padx=10, pady=2)
        
        save_settings_btn = tk.Button(settings_frame, text="💾 Save Settings",
                                    command=self.save_settings)
        self.apply_theme(save_settings_btn, "button")
        save_settings_btn.pack(pady=10)
    
    def scan_for_conflicts(self):
        """Scan for playlist conflicts"""
        def scan_thread():
            try:
                self.conflict_status.config(text="Scanning...")
                self.conflicts = detect_and_handle_conflicts(self.cfg, verbose=False)
                
                # Update UI
                self.root.after(0, self.update_conflicts_display)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Scan Error", f"Failed to scan: {e}"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_conflicts_display(self):
        """Update the conflicts display"""
        self.conflicts_listbox.delete(0, tk.END)
        
        if not self.conflicts:
            self.conflict_status.config(text="✅ No conflicts found")
            self.conflict_details.delete(1.0, tk.END)
            self.conflict_details.insert(1.0, "No conflicts detected.\nAll playlists are in sync!")
            return
        
        self.conflict_status.config(text=f"⚔️ {len(self.conflicts)} conflicts found")
        
        for i, conflict in enumerate(self.conflicts):
            pc_count = len([e for e in conflict.pc_version if not e.path.startswith('#')])
            phone_count = len([e for e in conflict.smartphone_version if not e.path.startswith('#')])
            
            display_text = f"{conflict.playlist_name} (PC:{pc_count} vs Phone:{phone_count})"
            self.conflicts_listbox.insert(tk.END, display_text)
    
    def on_conflict_select(self, event):
        """Handle conflict selection"""
        selection = self.conflicts_listbox.curselection()
        if not selection:
            return
        
        conflict_idx = selection[0]
        if conflict_idx < len(self.conflicts):
            conflict = self.conflicts[conflict_idx]
            
            # Display conflict details
            details = self.resolver.get_conflict_summary(conflict)
            
            self.conflict_details.delete(1.0, tk.END)
            self.conflict_details.insert(1.0, details)
            
            # Add content preview
            self.conflict_details.insert(tk.END, "\n\n=== PC VERSION ===\n")
            for entry in conflict.pc_version[:10]:  # Show first 10 entries
                self.conflict_details.insert(tk.END, f"{entry.path}\n")
            if len(conflict.pc_version) > 10:
                self.conflict_details.insert(tk.END, f"... and {len(conflict.pc_version) - 10} more entries\n")
            
            self.conflict_details.insert(tk.END, "\n=== PHONE VERSION ===\n")
            for entry in conflict.smartphone_version[:10]:  # Show first 10 entries
                self.conflict_details.insert(tk.END, f"{entry.path}\n")
            if len(conflict.smartphone_version) > 10:
                self.conflict_details.insert(tk.END, f"... and {len(conflict.smartphone_version) - 10} more entries\n")
    
    def resolve_selected_conflict(self, resolution):
        """Resolve the selected conflict with the chosen strategy"""
        selection = self.conflicts_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a conflict to resolve")
            return
        
        conflict_idx = selection[0]
        if conflict_idx >= len(self.conflicts):
            return
        
        conflict = self.conflicts[conflict_idx]
        
        # Confirm resolution
        confirm = messagebox.askyesno(
            "Confirm Resolution",
            f"Resolve conflict for '{conflict.playlist_name}' using {resolution.value.replace('_', ' ')}?\n\n"
            f"This will create a backup and update the playlist."
        )
        
        if not confirm:
            return
        
        def resolve_thread():
            try:
                from conversion import handle_single_conflict  # Fixed import
                
                # Temporarily set the resolution strategy
                original_resolution = self.cfg.conflict_resolution
                self.cfg.conflict_resolution = resolution
                
                # Resolve the conflict
                handle_single_conflict(conflict, self.cfg, verbose=True)
                
                # Restore original setting
                self.cfg.conflict_resolution = original_resolution
                
                # Update UI
                self.root.after(0, lambda: self.resolution_complete(conflict.playlist_name))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Resolution Error", f"Failed to resolve: {e}"))
        
        threading.Thread(target=resolve_thread, daemon=True).start()
    
    def resolution_complete(self, playlist_name):
        """Handle completion of conflict resolution"""
        messagebox.showinfo("Resolution Complete", f"Successfully resolved conflict for {playlist_name}")
        
        # Refresh the conflicts list
        self.scan_for_conflicts()
    
    def scan_for_duplicates(self):
        """Scan all playlists for duplicates"""
        def scan_thread():
            try:
                self.duplicate_status.config(text="Scanning...")
                
                # Scan for duplicates
                total_duplicates = scan_all_playlists_for_duplicates(self.cfg, verbose=False)
                
                # Get detailed statistics
                detailed_stats = {}
                
                for folder_key, folder_label in [("pc", "PC"), ("smartphone", "Smartphone")]:
                    folder_path = folders[folder_key]
                    folder_stats = []
                    
                    try:
                        for file in os.listdir(folder_path):
                            if file.endswith(".m3u"):
                                playlist_path = os.path.join(folder_path, file)
                                duplicates = self.resolver.find_duplicates(
                                    self.resolver.parse_playlist_file(playlist_path)
                                )
                                
                                if duplicates:
                                    duplicate_count = sum(len(indices) - 1 for indices in duplicates.values())
                                    folder_stats.append({
                                        'name': file,
                                        'duplicates': duplicate_count,
                                        'detail': duplicates
                                    })
                        
                        detailed_stats[folder_label] = folder_stats
                    except FileNotFoundError:
                        detailed_stats[folder_label] = []
                
                # Update UI
                self.root.after(0, lambda: self.update_duplicates_display(total_duplicates, detailed_stats))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Scan Error", f"Failed to scan: {e}"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_duplicates_display(self, total_duplicates, detailed_stats):
        """Update the duplicates display"""
        self.duplicates_text.delete(1.0, tk.END)
        
        if total_duplicates == 0:
            self.duplicate_status.config(text="✅ No duplicates found")
            self.duplicates_text.insert(1.0, "🎉 No duplicates found!\nAll your playlists are clean.")
            return
        
        self.duplicate_status.config(text=f"🔍 {total_duplicates} duplicates found")
        
        # Display summary
        self.duplicates_text.insert(tk.END, f"DUPLICATE ANALYSIS RESULTS\n")
        self.duplicates_text.insert(tk.END, f"=" * 50 + "\n\n")
        self.duplicates_text.insert(tk.END, f"Total duplicates found: {total_duplicates}\n\n")
        
        # Display details by folder
        for folder_label, stats in detailed_stats.items():
            self.duplicates_text.insert(tk.END, f"=== {folder_label} FOLDER ===\n")
            
            if not stats:
                self.duplicates_text.insert(tk.END, "No duplicates found in this folder.\n\n")
                continue
            
            for playlist_stat in stats:
                self.duplicates_text.insert(tk.END, f"\n📄 {playlist_stat['name']}\n")
                self.duplicates_text.insert(tk.END, f"   Duplicates: {playlist_stat['duplicates']}\n")
                
                # Show some examples
                for path, indices in list(playlist_stat['detail'].items())[:3]:  # Show first 3
                    filename = path.split('/')[-1] if '/' in path else path
                    self.duplicates_text.insert(tk.END, f"   • '{filename}' appears {len(indices)} times\n")
                
                if len(playlist_stat['detail']) > 3:
                    remaining = len(playlist_stat['detail']) - 3
                    self.duplicates_text.insert(tk.END, f"   ... and {remaining} more duplicate groups\n")
            
            self.duplicates_text.insert(tk.END, "\n")
    
    def remove_all_duplicates(self):
        """Remove duplicates from all playlists"""
        confirm = messagebox.askyesno(
            "Confirm Duplicate Removal",
            "This will remove ALL duplicates from ALL playlists in both PC and Smartphone folders.\n\n"
            "Backups will be created before making changes.\n\n"
            "Continue?"
        )
        
        if not confirm:
            return
        
        def remove_thread():
            try:
                self.duplicate_status.config(text="Removing duplicates...")
                
                total_removed = 0
                processed_count = 0
                
                for folder_key in ["pc", "smartphone"]:
                    folder_path = folders[folder_key]
                    try:
                        for file in os.listdir(folder_path):
                            if file.endswith(".m3u"):
                                playlist_path = os.path.join(folder_path, file)
                                removed = remove_duplicates_from_playlist(playlist_path, self.cfg)
                                total_removed += removed
                                processed_count += 1
                    except FileNotFoundError:
                        pass
                
                # Update UI
                self.root.after(0, lambda: self.removal_complete(total_removed, processed_count))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Removal Error", f"Failed to remove duplicates: {e}"))
        
        threading.Thread(target=remove_thread, daemon=True).start()
    
    def removal_complete(self, total_removed, processed_count):
        """Handle completion of duplicate removal"""
        if total_removed > 0:
            messagebox.showinfo(
                "Removal Complete",
                f"Successfully removed {total_removed} duplicates from {processed_count} playlists.\n\n"
                f"Backups have been created in the Backups folder."
            )
        else:
            messagebox.showinfo("No Duplicates", "No duplicates were found to remove.")
        
        # Refresh the duplicates scan
        self.scan_for_duplicates()
    
    def save_settings(self):
        """Save conflict resolution settings"""
        try:
            # Update the resolver's default resolution
            resolution_value = self.default_resolution.get()
            resolution = ConflictResolution(resolution_value)
            self.resolver.default_resolution = resolution
            self.cfg.conflict_resolution = resolution
            
            # Save to config file
            if self.config:
                self.config["default_conflict_resolution"] = resolution_value
                from config import save_config
                save_config(self.config)
            
            messagebox.showinfo("Settings Saved", "Conflict resolution settings have been saved.")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")

# Integration function to launch from main GUI
def launch_conflict_gui(config=None, theme="dark"):
    """Launch the conflict resolution GUI"""
    gui = ConflictResolutionGUI(config, theme)
    gui.launch()

# Standalone launcher
def main():
    """Standalone launcher for conflict resolution GUI"""
    from config import load_config
    
    config = load_config()
    if not config:
        print("❌ No configuration found. Please run PlaylistConverter setup first.")
        return
    
    print("🚀 Launching Conflict Resolution GUI...")
    launch_conflict_gui(config)

if __name__ == "__main__":
    main()