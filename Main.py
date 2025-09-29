# type: ignore
import os
import sys
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import json
from typing import Dict, Optional

# Debug Logger
try:
    from Logic.BackGround_Logic.Debug_Logger import debug_log, LogCategory  # type: ignore
    DEBUG_LOGGER_AVAILABLE = True
except ImportError:
    DEBUG_LOGGER_AVAILABLE = False
    # Fallback log categories
    from enum import Enum
    class LogCategory(Enum):  # type: ignore
        SYSTEM = "SYSTEM"
        UI = "UI"  
        ERROR = "ERROR"
        SCREEN_CAPTURE = "SCREEN_CAPTURE"
    def debug_log(category, message):  # type: ignore
        print(f"[{category.value}] {message}")

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    debug_log(LogCategory.SYSTEM, "Warning: keyboard library not available. Hotkeys will not work.")  # type: ignore

try:
    import customtkinter as ctk  # type: ignore
    CTK_AVAILABLE = True
except Exception:
    CTK_AVAILABLE = False
    ctk = None  # type: ignore

# Import the Roblox checker
from Logic.BackGround_Logic.Is_Roblox_Open import check_roblox_and_game


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "Logic", "Fishing_Script.py")
SETTINGS_FILE = os.path.join(BASE_DIR, "Logic", "BackGround_Logic", "hotkey_settings.json")
MINIGAME_SETTINGS_FILE = os.path.join(BASE_DIR, "Logic", "BackGround_Logic", "minigame_settings.json")

# Valid numpad keys for hotkeys
VALID_NUMPAD_KEYS = ['num 0', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5', 'num 6', 'num 7', 'num 8', 'num 9']
MODIFIER_KEYS = ['shift', 'ctrl', 'alt']


def resource_exists(path: str) -> bool:
    return os.path.isfile(path)


def load_hotkey_settings() -> Dict[str, str]:
    """Load hotkey settings from file."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error loading hotkey settings: {e}")
    
    # Default hotkeys
    return {
        'start_hotkey': 'num 1',
        'stop_hotkey': 'num 2'
    }


def save_hotkey_settings(settings: Dict[str, str]) -> None:
    """Save hotkey settings to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error saving hotkey settings: {e}")


def load_minigame_settings() -> Dict[str, float]:
    """Load minigame settings from file."""
    try:
        if os.path.exists(MINIGAME_SETTINGS_FILE):
            with open(MINIGAME_SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error loading minigame settings: {e}")
    
    # Default minigame settings (matching AHK values)
    return {
        'control_value': 0.0,
        'fish_bar_tolerance': 5,
        'white_bar_tolerance': 15,
        'arrow_tolerance': 6,
        'scan_delay': 10,
        'side_bar_ratio': 0.7,
        'side_bar_delay': 400,
        'stable_right_multiplier': 2.36,
        'stable_right_division': 1.55,
        'stable_left_multiplier': 1.211,
        'stable_left_division': 1.12,
        'unstable_right_multiplier': 2.665,
        'unstable_right_division': 1.5,
        'unstable_left_multiplier': 2.19,
        'unstable_left_division': 1.0,
        'right_ankle_break_multiplier': 0.75,
        'left_ankle_break_multiplier': 0.45
    }


def save_minigame_settings(settings: Dict[str, float]) -> None:
    """Save minigame settings to file."""
    try:
        with open(MINIGAME_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error saving minigame settings: {e}")


def is_valid_hotkey(hotkey: str) -> bool:
    """Check if a hotkey is valid (numpad keys with optional modifiers)."""
    if not hotkey or not hotkey.strip():
        return False
    
    hotkey = hotkey.lower().strip()
    
    # Split by + to check for modifiers
    parts = [part.strip() for part in hotkey.split('+')]
    
    # Last part should be a numpad key
    if parts[-1] not in VALID_NUMPAD_KEYS:
        return False
    
    # All other parts should be modifiers
    for part in parts[:-1]:
        if part not in MODIFIER_KEYS:
            return False
    
    return True


# determine the base class at runtime to ensure a proper class object is used
_BaseClass = ctk.CTk if ctk else tk.Tk

class _BaseLauncher(_BaseClass): # type: ignore
    """Base launcher using CustomTkinter when available or tkinter fallback."""
    pass


class LauncherApp(_BaseLauncher):
    def __init__(self):
        if ctk:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            super().__init__()
        else:
            super().__init__()

        self.title("Blox Fruit Fishing — Launcher")
        width, height = 800, 600  # Increased size for tabbed interface
        # Position window in top-right corner of screen
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        margin = 20  # Small margin from screen edges
        x = screen_w - width - margin  # Right side with margin
        y = margin  # Top side with margin
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        
        # Make window stay on top
        self.attributes('-topmost', True)
        self.focus_force()  # Force focus to the window
        self.topmost_enabled = True

        self.process = None
        
        # Load settings
        self.hotkey_settings = load_hotkey_settings()
        self.minigame_settings = load_minigame_settings()
        self.hotkeys_registered = False
        self.hotkey_entries = {}  # Store hotkey entry widgets
        self.minigame_entries = {}  # Store minigame entry widgets
        
        # Initialize hotkeys if keyboard library is available
        if KEYBOARD_AVAILABLE:
            self._setup_hotkeys()

        if ctk:
            self._build_modern_ui()
        else:
            self._build_basic_ui()

    def _build_modern_ui(self):
        # Create main container
        main_container = ctk.CTkFrame(self, corner_radius=18)  # type: ignore
        main_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95, relheight=0.95)

        # Create tabview
        tabview = ctk.CTkTabview(main_container, width=750, height=550)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add tabs
        tabview.add("General")
        tabview.add("Hotkeys")
        tabview.add("Minigame Settings")
        
        # Build General tab
        self._build_general_tab(tabview.tab("General"))
        
        # Build Hotkeys tab
        self._build_hotkeys_tab(tabview.tab("Hotkeys"))
        
        # Build Minigame Settings tab
        self._build_minigame_tab(tabview.tab("Minigame Settings"))

    def _build_general_tab(self, tab_frame):
        """Build the general/launcher tab."""
        # Title
        title = ctk.CTkLabel(tab_frame, text="Auto Fishing", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(pady=(20, 10))

        subtitle = ctk.CTkLabel(tab_frame, text="Launch the automated fishing script", font=ctk.CTkFont(size=12))
        subtitle.pack(pady=(0, 20))

        # Main button
        self.btn = ctk.CTkButton(
            tab_frame,
            text="Auto Fishing",
            width=260,
            height=70,
            corner_radius=14,
            fg_color="#1fb57a",
            hover_color="#199a63",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.on_start,
        )
        self.btn.pack(pady=(0, 15))

        # Topmost toggle button
        self.topmost_btn = ctk.CTkButton(
            tab_frame,
            text="📌 Always on Top: ON",
            width=200,
            height=25,
            corner_radius=8,
            fg_color="#444444",
            hover_color="#555555",
            font=ctk.CTkFont(size=11),
            command=self.toggle_topmost,
        )
        self.topmost_btn.pack(pady=(0, 10))

        # Tip
        hint = ctk.CTkLabel(tab_frame, text="Tip: Keep the game window open. Use hotkeys for quick start/stop.")
        hint.pack(pady=(20, 10))

    def _build_hotkeys_tab(self, tab_frame):
        """Build the dedicated hotkeys tab with scrollable content."""
        # Create scrollable frame for all content
        scrollable_frame = ctk.CTkScrollableFrame(tab_frame, width=700, height=500)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title = ctk.CTkLabel(scrollable_frame, text="Hotkey Configuration", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(20, 10))
        
        # Instructions (moved up to replace subtitle)
        instructions_frame = ctk.CTkFrame(scrollable_frame)
        instructions_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        instructions_title = ctk.CTkLabel(instructions_frame, text="Instructions", font=ctk.CTkFont(size=14, weight="bold"))
        instructions_title.pack(pady=(10, 5))
        
        instructions_text = ctk.CTkLabel(
            instructions_frame, 
            text="• Only numpad keys (num 0-9) are allowed\n• Hotkeys work globally - even when Roblox is focused\n• Make sure both hotkeys are different\n• Hotkeys are automatically saved",
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        instructions_text.pack(padx=20, pady=(0, 10))
        
        # Add hotkey configuration section
        self._add_hotkey_section(scrollable_frame)
        
        # Anti-Detection Settings
        anti_detection_frame = ctk.CTkFrame(scrollable_frame)
        anti_detection_frame.pack(fill="x", padx=20, pady=(10, 10))
        
        anti_detection_title = ctk.CTkLabel(anti_detection_frame, text="🛡️ Anti-Detection Settings", font=ctk.CTkFont(size=14, weight="bold"))
        anti_detection_title.pack(pady=(10, 5))
        
        # Disable auto-focus option
        self.disable_auto_focus = tk.BooleanVar(value=False)
        auto_focus_checkbox = ctk.CTkCheckBox(
            anti_detection_frame,
            text="Disable automatic window focusing (prevents Roblox anti-cheat detection)",
            variable=self.disable_auto_focus,
            font=ctk.CTkFont(size=11)
        )
        auto_focus_checkbox.pack(padx=20, pady=5)
        
        # Passive mode option (even safer)
        self.passive_mode = tk.BooleanVar(value=False)
        passive_mode_checkbox = ctk.CTkCheckBox(
            anti_detection_frame,
            text="Enable Passive Mode (100% undetectable - no input simulation)",
            variable=self.passive_mode,
            font=ctk.CTkFont(size=11),
            text_color="green"
        )
        passive_mode_checkbox.pack(padx=20, pady=5)
        
        anti_detection_note = ctk.CTkLabel(
            anti_detection_frame,
            text="⚠️ Passive Mode: Script only monitors, never sends input to Roblox\n💡 VirtualMouse: Uses hardware-level input (undetectable by anti-cheat)",
            font=ctk.CTkFont(size=10),
            text_color="orange"
        )
        anti_detection_note.pack(padx=20, pady=(0, 10))

    def _build_minigame_tab(self, tab_frame):
        """Build the minigame settings tab."""
        # Create scrollable frame for settings
        scrollable_frame = ctk.CTkScrollableFrame(tab_frame, width=700, height=500)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title = ctk.CTkLabel(scrollable_frame, text="!!!!! Check the Control stat of your Rod !!!!!", 
                           font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF6B6B")
        title.pack(pady=(10, 20))
        
        # Left column settings
        left_frame = ctk.CTkFrame(scrollable_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=5)
        
        # Control Value
        self._add_minigame_entry(left_frame, "Control Value:", "control_value", 0, 10)
        
        # Tolerances
        self._add_minigame_entry(left_frame, "Fish Bar Tolerance:", "fish_bar_tolerance", 5, 10)
        self._add_minigame_entry(left_frame, "White Bar Tolerance:", "white_bar_tolerance", 15, 10)
        self._add_minigame_entry(left_frame, "Arrow Tolerance:", "arrow_tolerance", 6, 10)
        
        # Timing
        self._add_minigame_entry(left_frame, "Scan Delay:", "scan_delay", 10, 10)
        self._add_minigame_entry(left_frame, "Side Bar Ratio:", "side_bar_ratio", 0.7, 10)
        self._add_minigame_entry(left_frame, "Side Bar Delay:", "side_bar_delay", 400, 10)
        
        # Right column settings
        right_frame = ctk.CTkFrame(scrollable_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=5)
        
        # Stable settings
        stable_label = ctk.CTkLabel(right_frame, text="Stable Settings", font=ctk.CTkFont(size=14, weight="bold"))
        stable_label.pack(pady=(10, 10))
        
        self._add_minigame_entry(right_frame, "Stable Right Multiplier:", "stable_right_multiplier", 2.36, 5)
        self._add_minigame_entry(right_frame, "Stable Right Division:", "stable_right_division", 1.55, 5)
        self._add_minigame_entry(right_frame, "Stable Left Multiplier:", "stable_left_multiplier", 1.211, 5)
        self._add_minigame_entry(right_frame, "Stable Left Division:", "stable_left_division", 1.12, 5)
        
        # Unstable settings
        unstable_label = ctk.CTkLabel(right_frame, text="Unstable Settings", font=ctk.CTkFont(size=14, weight="bold"))
        unstable_label.pack(pady=(20, 10))
        
        self._add_minigame_entry(right_frame, "Unstable Right Multiplier:", "unstable_right_multiplier", 2.665, 5)
        self._add_minigame_entry(right_frame, "Unstable Right Division:", "unstable_right_division", 1.5, 5)
        self._add_minigame_entry(right_frame, "Unstable Left Multiplier:", "unstable_left_multiplier", 2.19, 5)
        self._add_minigame_entry(right_frame, "Unstable Left Division:", "unstable_left_division", 1.0, 5)
        
        # Ankle Break settings
        ankle_label = ctk.CTkLabel(right_frame, text="Ankle Break Settings", font=ctk.CTkFont(size=14, weight="bold"))
        ankle_label.pack(pady=(20, 10))
        
        self._add_minigame_entry(right_frame, "Right Ankle Break Multiplier:", "right_ankle_break_multiplier", 0.75, 5)
        self._add_minigame_entry(right_frame, "Left Ankle Break Multiplier:", "left_ankle_break_multiplier", 0.45, 5)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=20)
        
        # Save and Load buttons
        save_btn = ctk.CTkButton(buttons_frame, text="Save Settings", width=120, command=self._save_minigame_settings)
        save_btn.pack(side="left", padx=(50, 10))
        
        load_btn = ctk.CTkButton(buttons_frame, text="Load Settings", width=120, command=self._load_minigame_settings)
        load_btn.pack(side="left", padx=10)
        
        reset_btn = ctk.CTkButton(buttons_frame, text="Reset to Defaults", width=120, command=self._reset_minigame_settings)
        reset_btn.pack(side="left", padx=10)

    def _add_minigame_entry(self, parent, label_text, key, default_value, pady=5):
        """Add a labeled entry for minigame settings."""
        entry_frame = ctk.CTkFrame(parent, fg_color="transparent")
        entry_frame.pack(fill="x", padx=10, pady=pady)
        
        label = ctk.CTkLabel(entry_frame, text=label_text, width=200, anchor="w")
        label.pack(side="left", padx=(0, 10))
        
        entry = ctk.CTkEntry(entry_frame, width=100, placeholder_text=str(default_value))
        entry.pack(side="right", padx=(10, 0))
        entry.insert(0, str(self.minigame_settings.get(key, default_value)))
        
        self.minigame_entries[key] = entry

    def _build_basic_ui(self):
        # Create notebook for tabs (basic tkinter version)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        # Hotkeys tab
        hotkeys_frame = ttk.Frame(notebook)
        notebook.add(hotkeys_frame, text="Hotkeys")
        
        # Minigame Settings tab
        minigame_frame = ttk.Frame(notebook)
        notebook.add(minigame_frame, text="Minigame Settings")
        
        # Build tabs
        self._build_general_tab_basic(general_frame)
        self._build_hotkeys_tab_basic(hotkeys_frame)
        self._build_minigame_tab_basic(minigame_frame)

    def _build_general_tab_basic(self, tab_frame):
        """Build the general tab for basic UI."""
        # Title
        title = tk.Label(tab_frame, text="Auto Fishing", font=("Segoe UI", 20, "bold"))
        title.pack(pady=(20, 10))

        subtitle = tk.Label(tab_frame, text="Launch the automated fishing script")
        subtitle.pack(pady=(0, 15))

        # Main button
        self.btn = tk.Button(tab_frame, text="Auto Fishing", width=30, height=2, command=self.on_start)
        self.btn.pack(pady=(0, 10))
        
        # Topmost toggle button
        self.topmost_btn = tk.Button(tab_frame, text="📌 Always on Top: ON", width=25, height=1, command=self.toggle_topmost)
        self.topmost_btn.pack(pady=(5, 10))

    def _build_hotkeys_tab_basic(self, tab_frame):
        """Build the hotkeys tab for basic UI with scrollable content."""
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(tab_frame)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Title
        title = tk.Label(scrollable_frame, text="Hotkey Configuration", font=("Segoe UI", 18, "bold"))
        title.pack(pady=(20, 10))

        # Instructions (moved up to replace subtitle)
        instructions_frame = tk.LabelFrame(scrollable_frame, text="Instructions", padx=20, pady=10)
        instructions_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        instructions_text = tk.Label(
            instructions_frame, 
            text="• Only numpad keys (num 0-9) are allowed\n• Hotkeys work globally - even when Roblox is focused\n• Make sure both hotkeys are different\n• Hotkeys are automatically saved",
            justify="left"
        )
        instructions_text.pack()
        
        # Add hotkey configuration section
        self._add_hotkey_section_basic(scrollable_frame)
        
        # Anti-Detection Settings
        anti_detection_frame = tk.LabelFrame(scrollable_frame, text="🛡️ Anti-Detection Settings", padx=20, pady=10)
        anti_detection_frame.pack(fill="x", padx=20, pady=(10, 10))
        
        # Disable auto-focus option
        if not hasattr(self, 'disable_auto_focus'):
            self.disable_auto_focus = tk.BooleanVar(value=False)
        auto_focus_checkbox = tk.Checkbutton(
            anti_detection_frame,
            text="Disable automatic window focusing (prevents anti-cheat detection)",
            variable=self.disable_auto_focus
        )
        auto_focus_checkbox.pack(anchor="w", pady=5)
        
        # Passive mode option (even safer)
        if not hasattr(self, 'passive_mode'):
            self.passive_mode = tk.BooleanVar(value=False)
        passive_mode_checkbox = tk.Checkbutton(
            anti_detection_frame,
            text="Enable Passive Mode (100% undetectable - no input simulation)",
            variable=self.passive_mode,
            fg="green"
        )
        passive_mode_checkbox.pack(anchor="w", pady=5)
        
        anti_detection_note = tk.Label(
            anti_detection_frame,
            text="⚠️ Passive Mode: Script only monitors, never sends input to Roblox\n💡 VirtualMouse: Uses hardware-level input (undetectable)",
            fg="orange",
            justify="left"
        )
        anti_detection_note.pack(pady=(5, 0))

    def _build_minigame_tab_basic(self, tab_frame):
        """Build the minigame settings tab for basic UI."""
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(tab_frame)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Title
        title = tk.Label(scrollable_frame, text="!!!!! Check the Control stat of your Rod !!!!!", 
                        font=("Segoe UI", 12, "bold"), fg="red")
        title.pack(pady=(10, 20))
        
        # Create two columns
        columns_frame = ttk.Frame(scrollable_frame)
        columns_frame.pack(fill="both", expand=True, padx=10)
        
        # Left column
        left_frame = ttk.LabelFrame(columns_frame, text="Basic Settings", padding=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Add basic settings
        self._add_minigame_entry_basic(left_frame, "Control Value:", "control_value", 0)
        self._add_minigame_entry_basic(left_frame, "Fish Bar Tolerance:", "fish_bar_tolerance", 5)
        self._add_minigame_entry_basic(left_frame, "White Bar Tolerance:", "white_bar_tolerance", 15)
        self._add_minigame_entry_basic(left_frame, "Arrow Tolerance:", "arrow_tolerance", 6)
        self._add_minigame_entry_basic(left_frame, "Scan Delay:", "scan_delay", 10)
        self._add_minigame_entry_basic(left_frame, "Side Bar Ratio:", "side_bar_ratio", 0.7)
        self._add_minigame_entry_basic(left_frame, "Side Bar Delay:", "side_bar_delay", 400)
        
        # Right column
        right_frame = ttk.LabelFrame(columns_frame, text="Advanced Settings", padding=10)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Stable settings
        stable_frame = ttk.LabelFrame(right_frame, text="Stable Settings", padding=5)
        stable_frame.pack(fill="x", pady=(0, 10))
        
        self._add_minigame_entry_basic(stable_frame, "Right Multiplier:", "stable_right_multiplier", 2.36)
        self._add_minigame_entry_basic(stable_frame, "Right Division:", "stable_right_division", 1.55)
        self._add_minigame_entry_basic(stable_frame, "Left Multiplier:", "stable_left_multiplier", 1.211)
        self._add_minigame_entry_basic(stable_frame, "Left Division:", "stable_left_division", 1.12)
        
        # Unstable settings
        unstable_frame = ttk.LabelFrame(right_frame, text="Unstable Settings", padding=5)
        unstable_frame.pack(fill="x", pady=(0, 10))
        
        self._add_minigame_entry_basic(unstable_frame, "Right Multiplier:", "unstable_right_multiplier", 2.665)
        self._add_minigame_entry_basic(unstable_frame, "Right Division:", "unstable_right_division", 1.5)
        self._add_minigame_entry_basic(unstable_frame, "Left Multiplier:", "unstable_left_multiplier", 2.19)
        self._add_minigame_entry_basic(unstable_frame, "Left Division:", "unstable_left_division", 1.0)
        
        # Ankle break settings
        ankle_frame = ttk.LabelFrame(right_frame, text="Ankle Break Settings", padding=5)
        ankle_frame.pack(fill="x")
        
        self._add_minigame_entry_basic(ankle_frame, "Right Multiplier:", "right_ankle_break_multiplier", 0.75)
        self._add_minigame_entry_basic(ankle_frame, "Left Multiplier:", "left_ankle_break_multiplier", 0.45)
        
        # Buttons
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill="x", pady=20)
        
        save_btn = tk.Button(buttons_frame, text="Save Settings", command=self._save_minigame_settings)
        save_btn.pack(side="left", padx=(50, 10))
        
        load_btn = tk.Button(buttons_frame, text="Load Settings", command=self._load_minigame_settings)
        load_btn.pack(side="left", padx=10)
        
        reset_btn = tk.Button(buttons_frame, text="Reset to Defaults", command=self._reset_minigame_settings)
        reset_btn.pack(side="left", padx=10)

    def _add_minigame_entry_basic(self, parent, label_text, key, default_value):
        """Add a labeled entry for minigame settings (basic UI)."""
        entry_frame = ttk.Frame(parent)
        entry_frame.pack(fill="x", pady=2)
        
        label = tk.Label(entry_frame, text=label_text, width=18, anchor="w")
        label.pack(side="left")
        
        entry = tk.Entry(entry_frame, width=10)
        entry.pack(side="right", padx=(10, 0))
        entry.insert(0, str(self.minigame_settings.get(key, default_value)))
        
        self.minigame_entries[key] = entry

    def _save_minigame_settings(self):
        """Save minigame settings from GUI to file."""
        try:
            # Collect settings from entries
            new_settings = {}
            for key, entry in self.minigame_entries.items():
                try:
                    value = entry.get().strip()
                    # Convert to float
                    new_settings[key] = float(value)
                except ValueError:
                    messagebox.showerror("Invalid Value", f"Invalid value for {key}: '{value}'. Please enter a valid number.")
                    return
            
            # Save to file
            save_minigame_settings(new_settings)
            self.minigame_settings = new_settings
            
            messagebox.showinfo("Success", "Minigame settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving minigame settings: {str(e)}")

    def _load_minigame_settings(self):
        """Load minigame settings from file to GUI."""
        try:
            # Reload from file
            self.minigame_settings = load_minigame_settings()
            
            # Update GUI entries
            for key, entry in self.minigame_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(self.minigame_settings.get(key, 0)))
            
            messagebox.showinfo("Success", "Minigame settings loaded successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading minigame settings: {str(e)}")

    def _reset_minigame_settings(self):
        """Reset minigame settings to defaults."""
        try:
            # Get default settings
            default_settings = load_minigame_settings.__defaults__[0] if hasattr(load_minigame_settings, '__defaults__') else {
                'control_value': 0.0,
                'fish_bar_tolerance': 5,
                'white_bar_tolerance': 15,
                'arrow_tolerance': 6,
                'scan_delay': 10,
                'side_bar_ratio': 0.7,
                'side_bar_delay': 400,
                'stable_right_multiplier': 2.36,
                'stable_right_division': 1.55,
                'stable_left_multiplier': 1.211,
                'stable_left_division': 1.12,
                'unstable_right_multiplier': 2.665,
                'unstable_right_division': 1.5,
                'unstable_left_multiplier': 2.19,
                'unstable_left_division': 1.0,
                'right_ankle_break_multiplier': 0.75,
                'left_ankle_break_multiplier': 0.45
            }
            
            # Update GUI entries
            for key, entry in self.minigame_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(default_settings.get(key, 0)))
            
            messagebox.showinfo("Reset Complete", "Minigame settings reset to defaults. Don't forget to save!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error resetting minigame settings: {str(e)}")

    # status label intentionally removed per user request

    def toggle_topmost(self):
        """Toggle the always-on-top behavior of the window."""
        self.topmost_enabled = not self.topmost_enabled
        self.attributes('-topmost', self.topmost_enabled)
        
        # Update button text
        status_text = "ON" if self.topmost_enabled else "OFF"
        button_text = f"📌 Always on Top: {status_text}"
        
        if ctk and hasattr(self.topmost_btn, 'configure'):
            self.topmost_btn.configure(text=button_text)
        elif hasattr(self.topmost_btn, 'config'):
            self.topmost_btn.config(text=button_text)

    def on_start(self):
        if not resource_exists(SCRIPT_PATH):
            messagebox.showerror("Script not found", f"Could not find:\n{SCRIPT_PATH}")
            return

        if self.process and self.process.poll() is None:
            # process is running -> stop it
            self._stop_process()
            return

        # Check Roblox status before starting
        try:
            roblox_status = check_roblox_and_game()
            
            if not roblox_status['can_proceed']:
                # Ask user if they want to wait for Roblox/Blox Fruits
                retry_msg = f"{roblox_status['message']}\n\nWould you like to wait and retry automatically?"
                retry = messagebox.askyesno("Roblox Check Failed", retry_msg)
                
                if retry:
                    # Disable button and wait for Roblox/Blox Fruits
                    if ctk:
                        self.btn.configure(state="disabled", text="Waiting for Blox Fruits...")
                    else:
                        self.btn.configure(state="disabled", text="Waiting for Blox Fruits...")
                    
                    threading.Thread(target=self._wait_for_blox_fruits, daemon=True).start()
                return
            # If can_proceed is True, just continue to start the script automatically
            # No success message needed - just start the fishing
        except Exception as e:
            messagebox.showerror("Roblox Check Error", f"Failed to check Roblox status: {str(e)}")
            return

        # disable button and start
        try:
            if ctk:
                self.btn.configure(state="disabled", text="Starting...")
            else:
                self.btn.configure(state="disabled", text="Starting...")

            threading.Thread(target=self._launch_script, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            if ctk:
                self.btn.configure(state="normal", text="Auto Fishing")
            else:
                self.btn.configure(state="normal", text="Auto Fishing")

    def _launch_script(self):
        try:
            # Note: Window focusing is now handled by the fishing script itself
            debug_log(LogCategory.UI, "Starting fishing script...")
            
            # launching - status updates removed
            # spawn the script in a separate process so GUI stays responsive
            self.process = subprocess.Popen([sys.executable, SCRIPT_PATH], cwd=os.path.dirname(SCRIPT_PATH))
            # process started
            # re-enable button to allow stopping
            if ctk:
                self.btn.configure(state="normal", text="Stop Auto Fishing", command=self.on_start)
            else:
                self.btn.configure(state="normal", text="Stop Auto Fishing", command=self.on_start)

            # wait for process to exit
            self.process.wait()
            # process stopped
            if ctk:
                self.btn.configure(text="Auto Fishing", command=self.on_start)
            else:
                self.btn.configure(text="Auto Fishing", command=self.on_start)

        except Exception as e:
            messagebox.showerror("Launch failed", str(e))
            # error occurred (no status widget)
            if ctk:
                self.btn.configure(state="normal", text="Auto Fishing")
            else:
                self.btn.configure(state="normal", text="Auto Fishing")

    def _wait_for_blox_fruits(self):
        """Wait for user to open Blox Fruits, then automatically start the script."""
        from Logic.BackGround_Logic.Is_Roblox_Open import RobloxChecker
        
        try:
            checker = RobloxChecker()
            # Wait up to 60 seconds for Blox Fruits
            if checker.wait_for_blox_fruits(timeout=60):
                # Blox Fruits detected, start the script
                messagebox.showinfo("Success", "Blox Fruits detected! Starting the fishing script...")
                threading.Thread(target=self._launch_script, daemon=True).start()
            else:
                # Timeout reached
                messagebox.showwarning("Timeout", "Timeout reached. Please open Blox Fruits and try again.")
                # Re-enable button
                if ctk:
                    self.btn.configure(state="normal", text="Auto Fishing")
                else:
                    self.btn.configure(state="normal", text="Auto Fishing")
        except Exception as e:
            messagebox.showerror("Error", f"Error while waiting for Blox Fruits: {str(e)}")
            # Re-enable button
            if ctk:
                self.btn.configure(state="normal", text="Auto Fishing")
            else:
                self.btn.configure(state="normal", text="Auto Fishing")

    def _stop_process(self):
        if not self.process:
            return
        if self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        if ctk:
            self.btn.configure(text="Auto Fishing", command=self.on_start)
        else:
            self.btn.configure(text="Auto Fishing", command=self.on_start)

    def _add_hotkey_section(self, container):
        """Add hotkey configuration section to modern UI."""
        if not KEYBOARD_AVAILABLE:
            return
            
        # Hotkey section frame
        hotkey_frame = ctk.CTkFrame(container, corner_radius=12)
        hotkey_frame.pack(fill="x", padx=20, pady=(10, 10))
        
        hotkey_title = ctk.CTkLabel(hotkey_frame, text="Hotkeys", font=ctk.CTkFont(size=16, weight="bold"))
        hotkey_title.pack(pady=(10, 5))
        
        # Start hotkey
        start_frame = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
        start_frame.pack(fill="x", padx=10, pady=5)
        
        start_label = ctk.CTkLabel(start_frame, text="START:", width=60, font=ctk.CTkFont(size=12, weight="bold"))
        start_label.pack(side="left", padx=(0, 10))
        
        self.hotkey_entries['start'] = ctk.CTkEntry(
            start_frame, 
            width=120, 
            placeholder_text="e.g., num 1 or shift+num 1"
        )
        self.hotkey_entries['start'].pack(side="left", padx=(0, 10))
        self.hotkey_entries['start'].insert(0, self.hotkey_settings['start_hotkey'])
        
        # Stop hotkey
        stop_frame = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
        stop_frame.pack(fill="x", padx=10, pady=5)
        
        stop_label = ctk.CTkLabel(stop_frame, text="STOP:", width=60, font=ctk.CTkFont(size=12, weight="bold"))
        stop_label.pack(side="left", padx=(0, 10))
        
        self.hotkey_entries['stop'] = ctk.CTkEntry(
            stop_frame, 
            width=120, 
            placeholder_text="e.g., num 2 or ctrl+num 2"
        )
        self.hotkey_entries['stop'].pack(side="left", padx=(0, 10))
        self.hotkey_entries['stop'].insert(0, self.hotkey_settings['stop_hotkey'])
        
        # Apply button
        apply_btn = ctk.CTkButton(
            hotkey_frame, 
            text="Apply Hotkeys", 
            width=140, 
            height=28,
            command=self._apply_hotkeys,
            font=ctk.CTkFont(size=11)
        )
        apply_btn.pack(pady=(5, 10))
        
        # Info text
        info_text = "Use numpad keys (num 0-9) with optional modifiers (shift, ctrl, alt)"
        info_label = ctk.CTkLabel(hotkey_frame, text=info_text, font=ctk.CTkFont(size=10), text_color="gray")
        info_label.pack(pady=(0, 10))

    def _add_hotkey_section_basic(self, frame):
        """Add hotkey configuration section to basic UI."""
        if not KEYBOARD_AVAILABLE:
            return
            
        # Hotkey section frame
        hotkey_frame = tk.LabelFrame(frame, text="Hotkeys", font=("Segoe UI", 10, "bold"), padx=10, pady=5)
        hotkey_frame.pack(fill="x", padx=10, pady=(5, 5))
        
        # Start hotkey
        start_frame = tk.Frame(hotkey_frame)
        start_frame.pack(fill="x", pady=2)
        
        start_label = tk.Label(start_frame, text="START:", width=8, font=("Segoe UI", 9, "bold"))
        start_label.pack(side="left")
        
        self.hotkey_entries['start'] = tk.Entry(start_frame, width=20)
        self.hotkey_entries['start'].pack(side="left", padx=(5, 0))
        self.hotkey_entries['start'].insert(0, self.hotkey_settings['start_hotkey'])
        
        # Stop hotkey
        stop_frame = tk.Frame(hotkey_frame)
        stop_frame.pack(fill="x", pady=2)
        
        stop_label = tk.Label(stop_frame, text="STOP:", width=8, font=("Segoe UI", 9, "bold"))
        stop_label.pack(side="left")
        
        self.hotkey_entries['stop'] = tk.Entry(stop_frame, width=20)
        self.hotkey_entries['stop'].pack(side="left", padx=(5, 0))
        self.hotkey_entries['stop'].insert(0, self.hotkey_settings['stop_hotkey'])
        
        # Apply button
        apply_btn = tk.Button(hotkey_frame, text="Apply Hotkeys", command=self._apply_hotkeys)
        apply_btn.pack(pady=(5, 0))
        
        # Info text
        info_label = tk.Label(hotkey_frame, text="Use numpad keys (num 0-9) with optional modifiers", 
                             font=("Segoe UI", 8), fg="gray")
        info_label.pack()

    def _setup_hotkeys(self):
        """Set up hotkey listeners."""
        if not KEYBOARD_AVAILABLE or self.hotkeys_registered:
            return
            
        try:
            # Register hotkeys
            start_hotkey = self.hotkey_settings['start_hotkey']
            stop_hotkey = self.hotkey_settings['stop_hotkey']
            
            if is_valid_hotkey(start_hotkey):
                keyboard.add_hotkey(start_hotkey, self._hotkey_start)
            
            if is_valid_hotkey(stop_hotkey) and start_hotkey != stop_hotkey:
                keyboard.add_hotkey(stop_hotkey, self._hotkey_stop)
            
            self.hotkeys_registered = True
            debug_log(LogCategory.SYSTEM, f"Hotkeys registered: Start={start_hotkey}, Stop={stop_hotkey}")
            
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error setting up hotkeys: {e}")

    def _clear_hotkeys(self):
        """Clear all registered hotkeys."""
        if not KEYBOARD_AVAILABLE or not self.hotkeys_registered:
            return
            
        try:
            keyboard.clear_all_hotkeys()
            self.hotkeys_registered = False
            debug_log(LogCategory.SYSTEM, "All hotkeys cleared")
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error clearing hotkeys: {e}")

    def _apply_hotkeys(self):
        """Apply new hotkey settings."""
        if not KEYBOARD_AVAILABLE:
            messagebox.showerror("Error", "Keyboard library not available for hotkeys!")
            return
            
        try:
            # Get new hotkeys from entries
            start_hotkey = self.hotkey_entries['start'].get().strip()
            stop_hotkey = self.hotkey_entries['stop'].get().strip()
            
            # Validate hotkeys
            if not is_valid_hotkey(start_hotkey):
                messagebox.showerror("Invalid Hotkey", 
                    f"Invalid start hotkey: '{start_hotkey}'\n"
                    "Use numpad keys (num 0-9) with optional modifiers (shift, ctrl, alt)\n"
                    "Examples: 'num 1', 'shift+num 1', 'ctrl+num 5'")
                return
                
            if not is_valid_hotkey(stop_hotkey):
                messagebox.showerror("Invalid Hotkey", 
                    f"Invalid stop hotkey: '{stop_hotkey}'\n"
                    "Use numpad keys (num 0-9) with optional modifiers (shift, ctrl, alt)\n"
                    "Examples: 'num 2', 'shift+num 2', 'alt+num 9'")
                return
            
            if start_hotkey == stop_hotkey:
                messagebox.showerror("Duplicate Hotkeys", 
                    "Start and stop hotkeys cannot be the same!")
                return
            
            # Clear existing hotkeys
            self._clear_hotkeys()
            
            # Update settings
            self.hotkey_settings['start_hotkey'] = start_hotkey
            self.hotkey_settings['stop_hotkey'] = stop_hotkey
            
            # Save settings
            save_hotkey_settings(self.hotkey_settings)
            
            # Re-register hotkeys
            self._setup_hotkeys()
            
            messagebox.showinfo("Hotkeys Updated", 
                f"Hotkeys successfully updated!\n"
                f"Start: {start_hotkey}\n"
                f"Stop: {stop_hotkey}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error applying hotkeys: {str(e)}")

    def _hotkey_start(self):
        """Handle start hotkey press."""
        try:
            # Only start if not already running
            if not self.process or self.process.poll() is not None:
                self.on_start()
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error in start hotkey: {e}")

    def _hotkey_stop(self):
        """Handle stop hotkey press."""
        try:
            # Only stop if currently running
            if self.process and self.process.poll() is None:
                self._stop_process()
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error in stop hotkey: {e}")

    def destroy(self):
        """Clean up hotkeys when closing the application."""
        self._clear_hotkeys()
        super().destroy()



if __name__ == "__main__":
    # Don't print noisy messages on startup; GUI will fall back to tkinter automatically
    app = LauncherApp()
    app.mainloop()
