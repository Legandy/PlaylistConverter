🎧 PlaylistConverter
Automatically detects changes .m3u8 files to .m3u (to work with MusicBee), converts absolute paths to relative paths, maintains backups, and keeps your Android and Library folders in sync — all in real time.

🚀 Features
- 🧠 Hash-based change detection — only processes playlists when content changes
- 🔁 Bidirectional sync — Android ↔ Library
- 📂 Conversion folder — stores the latest version of each playlist
- 💾 Backup system — keeps timestamped copies with configurable limits
- 🐶 Watchdog monitoring — reacts instantly to file changes
- 🧹 Extension normalization — renames .m3u8 to .m3u for compatibility
- 🖼️ System tray icon — optional GUI with right-click menu
- ⚙️ Autostart support — can run silently on system boot
- 🧩 Interactive configuration — no need to edit the script manually
- 🔄 Path conversion — transforms absolute paths into relative ones for portability

📁 What is Path Conversion?
Many playlist editors (like MusicBee) save tracks using absolute paths, such as:
C:\Users\Andre\Music\Rock\song.mp3


But Android apps like Poweramp expect relative paths, like:
Rock/song.mp3


This script automatically converts absolute paths to relative ones so your playlists work seamlessly across devices — no broken links, no manual editing.
✅ Why it matters:
- Makes playlists portable between PC and phone
- Avoids hardcoded drive letters or user folders
- Ensures Poweramp can read and play the tracks

📁 Folder Structure
PlaylistsAndre/
├── Android/        # Poweramp playlists
├── Library/        # MusicBee playlists
├── Conversion/     # Latest converted playlists
├── Backups/        # Timestamped backups
├── Logs/           # Log file with sync history
└── PlaylistConverter.pyw



🛠 Setup
- Install dependencies:
pip install watchdog pillow pystray
- Run the script:
- Double-click PlaylistConverter.pyw
- Follow the prompts:
- 📂 Base folder path
- 🔢 Max backups per playlist
- ⏳ Process delay (seconds)
- 🕒 Block duration after push (seconds)
- Optional: Add a custom tray icon
Save playlist_icon.ico next to your script

🖥️ Tray Menu
If enabled, the tray icon provides:
- ▶️ Run Sync — manually trigger sync
- 📤 Quit — stop the app and exit gracefully

⚙️ Configuration Options
| Option | Description | Default | 
| Base Folder | Root folder for all playlist operations | — | 
| Max Backups | Number of backups per playlist | 10 | 
| Process Delay | Debounce time to avoid rapid reprocessing | 2 sec | 
| Block Duration | Ignore window after pushing a file | 2 sec | 



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



🎨 Icon Credit
Tray icon used with permission from:
<a href="https://www.flaticon.com/free-icons/playlist" title="playlist icons">Playlist icons created by Freepik - Flaticon</a>

📄 License
This project is licensed under the GNU General Public License v3.0 (GPLv3).
You are free to use, modify, and distribute this software, as long as any derivative works are also licensed under GPLv3.
Copyright (c) 2024 Legandy
See the LICENSE file for full details.


🤝 Contributions
Feel free to fork, improve, and share — just keep it open-source.
For commercial use or licensing inquiries, contact Legandy.

💬 Questions or Feedback?
Open an issue or start a discussion — I’d love to hear how you’re using PlaylistConverter!