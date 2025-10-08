# Blox Fruit Fishing Macro

Automate fishing and other repetitive tasks in Roblox Blox Fruits with a desktop launcher that keeps itself up to date, installs dependencies, and exposes a GUI for controlling macros.

> **Heads up:** Roblox must stay in normal quality. Fast Mode breaks the automation logic.

## ✨ Current Capabilities

- **Auto Fishing (GUI first)** – Core minigame logic is ~98% complete and works best with the included templates.
- **Enhanced Fish Detection** – Uses OpenCV template matching with adaptive resizing for better accuracy.
- **Hotkey Controls** – Default numpad bindings (1 = start, 2 = stop) with in-app customization.
- **Diagnostics & Logging** – `tests/quick_test.py` validates critical modules before launch.
- **Auto-Updater** – Checks GitHub releases and can self-update through the launcher.

## 🔭 Roadmap & Experiments

- **Auto Bone Grinding** – Currently works with Elemental fruits; see the guide below.
- **Auto Webhook Notifications** – Planned for status updates while the macro runs.
- **PvP Aim Assist** – Prototype adds subtle Ken-based tracking.
- **Combo Loader** – Build and share custom combo scripts.
- **Up Trader** – Planned value checker using <https://bloxfruitsvalues.com/values> to avoid unfair trades (targeting a configurable 5%+ profit margin).

### Reference Images

[![Fish ReadMe](Images/Readme/FISHREADME.png)](Images/Readme/FISHREADME.png)

[![Bones ReadMe](Images/Readme/Bones_ReadMe.png)](Images/Readme/Bones_ReadMe.png)

## 🚀 Getting Started

1. **Download the release** from GitHub and extract it anywhere outside of restricted folders (avoid Program Files).
2. **Run the launcher** (recommended order):
   - Double-click `Launcher.exe` *(built with PyInstaller; includes update checks, dependency installs, quick tests, and GUI launch)*.
   - Alternatively, run the Python script directly:

     ```powershell
     python Launcher.py
     ```

   - Legacy option: `Run_Me.bat` is still available but may trigger antivirus false positives on some machines.
3. **Follow the console prompts** to install dependencies, run diagnostics, and launch the GUI. Keep Roblox focused on the correct screen region for accurate template matching.

## 🛠️ Building Your Own `Launcher.exe`

If you want to regenerate the executable yourself (or customize the launcher), install PyInstaller and bundle the script:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile Launcher.py
```

The compiled binary will be located at `dist/Launcher.exe`. Ship it along with the project files so templates and scripts remain accessible.

## 🤝 Support & Feedback

- Report issues, share combo ideas, or request features on Discord: [https://discord.gg/dHUM2ejQGY](https://discord.gg/dHUM2ejQGY)
- Pull requests and bug reports are welcome on GitHub—especially around new detection templates or gameplay tweaks.
