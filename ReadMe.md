🎧 PlaylistConverter
Smart playlist sync tool for MusicBee and Poweramp.
Automatically detects changes in .m3u and .m3u8 files, converts absolute paths to relative paths, maintains backups, and keeps your Android and Library folders in sync — all in real time.

🚀 Features
- 🧠 Hash-based change detection — only processes playlists when content changes
- 🔁 Bidirectional sync — Android ↔ Library
- 📂 Conversion folder — stores the latest version of each playlist
- 💾 Backup system — keeps timestamped copies with configurable limits
- 🐶 Watchdog monitoring — reacts instantly to file changes
- 🧹 Extension normalization — renames .m3u8 to .m3u for compatibility
- 🖼️ System tray icon — optional GUI with right-click menu
- ⚙️ Autostart support — can run silently on system boot

📁 Folder Structure
Playlists/
├── Android/        # Poweramp playlists
├── Library/        # MusicBee playlists
├── Conversion/     # Latest converted playlists
├── Backups/        # Timestamped backups
├── Logs/           # Log file with sync history
└── PlaylistConverter.pyw



🛠 Setup
- Install dependencies:
pip install watchdog pillow pystray
- Place your .m3u or .m3u8 playlists in Android/ or Library/
- Run the script:
- Double-click PlaylistConverter.pyw
- Or add it to Windows Startup folder for autostart

🖥️ Tray Menu (optional)
If enabled, the tray icon provides:
- ▶️ Run Sync — manually trigger sync
- 📤 Quit — stop the app and exit gracefully

⚙️ Configuration
You can tweak these values at the top of the script:
MAX_BACKUPS = 5         # Backups per playlist
PROCESS_DELAY = 2       # Debounce time in seconds
BLOCK_DURATION = 3      # Ignore window after push



📓 Logs
All sync activity is logged to:
Logs/log.txt



📦 Autostart (Windows)
To run on boot:
- Create a .bat file:
@echo off
start "" "C:\Path\To\PlaylistConverter.pyw"
- Place it in:
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup



🧠 Notes
- .m3u8 files are automatically renamed to .m3u in Android folder
- Only changed playlists are processed — no duplicates
- Backups are stored separately and rotated automatically

Credits:
<a target="_blank" href="https://icons8.com/icon/mjtxCfHlksr0/playlist">Playlist</a> icon by <a target="_blank" href="https://icons8.com">Icons8</a>

