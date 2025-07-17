# 🎧 PlaylistConverter

**PlaylistConverter** is a lightweight desktop utility that watches your playlist folders and keeps them in sync — automatically converting `.m3u8` files to `.m3u`, rewriting absolute paths to relative ones, and maintaining backups.  
It runs quietly in the background and offers a tray icon for quick access.

---

## 🚀 Features

- 🧠 Hash-based change detection — only processes playlists when content changes  
- 🔁 Bidirectional sync — keeps Android and Library folders in sync  
- 📂 Conversion folder — stores the latest version of each playlist  
- 💾 Backup system — keeps timestamped copies with configurable limits  
- 🐶 Watchdog monitoring — reacts instantly to file changes  
- 🧹 Extension normalization — renames `.m3u8` to `.m3u` for compatibility  
- 🖼️ System tray icon — optional GUI with right-click menu  
- ⚙️ Autostart support — can run silently on system boot  
- 🧩 Interactive configuration — no need to edit the script manually  
- 🔄 Path conversion — transforms absolute paths into relative ones for portability  

---

## 📁 What Is Path Conversion?

Many playlist editors save tracks using **absolute paths**, like:

```
C:\Users\YourName\Music\song.mp3
```

But many mobile apps (like Poweramp) expect **relative paths**, such as:

```
Music\song.mp3
```

Your folder structure has to be the same on all devices.
For example:
PC: C:\Music\song.mp3
Android: /storage/emulated/0/Music/song.mp3


This script automatically converts absolute paths to relative ones so your playlists work seamlessly across devices — no broken links, no manual editing.

✅ Why it matters:
- Makes playlists portable between PC and phone  
- Avoids hardcoded drive letters or user folders  
- Ensures compatibility with apps that expect relative paths  

> 💡 You don’t need to use MusicBee or Poweramp — they’re just examples.  


Different Music players i tried:
Windows:
- MediaMonkey -> stores internal playlists in a Database -> can't be overridden via new file
- AIMP -> stores playlist as a file but as a .aimppl4 -> conversion possible but not implemented
- MusicBee -> stores playlist in a m3u file -> easily overridden -> Winner

Android:
- Poweramp -> imports playlist automatically and writes new entries into the m3u files
---

Syncing across devices:
- For syncing the playlists with relative paths I use ResilioSync but SyncThing should work too

📁 Folder Structure (Fully Customizable)
Playlists/                  # Example base folder (user-defined)
├── Android/                → 📂 Mobile playlists folder (user-defined name & path)
├── Library/                → 📂 Desktop playlists folder (user-defined name & path)

PlaylistConverter/          # App-managed folders (auto-created)
├── Conversion/             → Latest converted playlists
├── Backups/                → Timestamped backups
├── Logs/                   → Log file with sync history
└── PlaylistConverter.pyw   → Main script


💡 You choose the names and locations of your Android and Library folders during setup.
They don’t need to be called “Android” or “Library” — those are just examples.


🧩 Setup Prompts
When you run the script, you’ll be asked to select:
- 📂 Base folder (e.g. Playlists/)
- 📱 Mobile playlist folder (e.g. PowerampPlaylists/)
- 💻 Desktop playlist folder (e.g. MusicBeePlaylists/)
- 🔢 Max backups per playlist
- ⏳ Process delay (seconds)
- 🕒 Block duration after push (seconds)
- ⚙️ Enable autostart?
All paths are saved in config.json and can be changed anytime via the tray menu’s Reset Setup.


---

## 🛠 Setup

1. Dependencies:
    - Python

And Install python dependencies:

    pip install watchdog pillow pystray

2. Run the script:
   - Double-click `PlaylistConverter.pyw`
   - Follow the prompts:
     - 📂 Base folder path  
     - 🔢 Max backups per playlist  
     - ⏳ Process delay (seconds)  
     - 🕒 Block duration after push (seconds)  

3. Optional:
   - Add a custom tray icon:  
     Save `playlist_icon.ico` next to your script

---

## 🖥️ Tray Menu

If enabled, the tray icon provides:

- ▶️ **Run Sync** — manually trigger sync  
- 📂 **Open Folder** — open your base folder  (Playlists)
- 🔁 **Toggle Autostart** — enable/disable startup  
- 🔄 **Reset Setup** — reconfigure everything  
- ❌ **Quit** — exit the app  

---

## ⚙️ Configuration Options

| Option          | Description                                 | Default |
|-----------------|---------------------------------------------|---------|
| Base Folder     | Root folder for all playlist operations     | —       |
| Max Backups     | Number of backups per playlist              | 10      |
| Process Delay   | Debounce time to avoid rapid reprocessing   | 2 sec   |
| Block Duration  | Ignore window after pushing a file          | 2 sec   |

---

## 📓 Logs

All sync activity is logged to:

```
Logs/log.txt
```

## 🎨 Icon Credit

Tray icon used with permission from:  
<a href="https://www.flaticon.com/free-icons/playlist" title="playlist icons">Playlist icons created by Freepik - Flaticon</a>

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
You are free to use, modify, and distribute this software, as long as any derivative works are also licensed under GPLv3.

**Copyright (c) 2024 Legandy**

See the [LICENSE](LICENSE) file for full details.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)