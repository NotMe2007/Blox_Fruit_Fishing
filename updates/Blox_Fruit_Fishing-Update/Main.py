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

# Debug Logger - Import from centralized Import_Utils
try:
    from Logic.BackGround_Logic.Import_Utils import debug_log, LogCategory, DEBUG_LOGGER_AVAILABLE  # type: ignore
except ImportError:
    # Fallback if Import_Utils not available
    DEBUG_LOGGER_AVAILABLE = False
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
SETTINGS_DIR = os.path.join(BASE_DIR, "Logic", "BackGround_Logic", "settings")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "hotkey_settings.json")
MINIGAME_SETTINGS_FILE = os.path.join(SETTINGS_DIR, "minigame_settings.json")
GENERAL_SETTINGS_FILE = os.path.join(SETTINGS_DIR, "general_settings.json")

# Valid keys for hotkeys
VALID_NUMPAD_KEYS = ['num 0', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5', 'num 6', 'num 7', 'num 8', 'num 9', 'num *', 'num /', 'num .']
VALID_LETTER_KEYS = ['p', 'f', 'g', 'h', 'k', 'l', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '?', "'", '`']
VALID_HOTKEY_KEYS = VALID_NUMPAD_KEYS + VALID_LETTER_KEYS
INVALID_REGULAR_NUMBERS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
MODIFIER_KEYS = ['shift', 'ctrl', 'alt']


def ensure_settings_dir() -> None:
    """Ensure the settings directory exists."""
    if not os.path.exists(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR, exist_ok=True)


def resource_exists(path: str) -> bool:
    return os.path.isfile(path)


def load_hotkey_settings() -> Dict[str, str]:
    """Load hotkey settings from file."""
    ensure_settings_dir()
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
    ensure_settings_dir()
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error saving hotkey settings: {e}")


def load_general_settings() -> Dict[str, bool]:
    """Load general settings from file."""
    ensure_settings_dir()
    try:
        if os.path.exists(GENERAL_SETTINGS_FILE):
            with open(GENERAL_SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error loading general settings: {e}")
    
    # Default general settings
    return {
        'disable_auto_focus': False,
        'passive_mode': False,
        'topmost_enabled': True
    }


def save_general_settings(settings: Dict[str, bool]) -> None:
    """Save general settings to file."""
    ensure_settings_dir()
    try:
        with open(GENERAL_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error saving general settings: {e}")


def load_minigame_settings() -> Dict[str, float]:
    """Load minigame settings from file."""
    ensure_settings_dir()
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
    ensure_settings_dir()
    try:
        with open(MINIGAME_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        debug_log(LogCategory.ERROR, f"Error saving minigame settings: {e}")


def is_valid_hotkey(hotkey: str) -> tuple[bool, str]:
    """Check if a hotkey is valid and return validation message.
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not hotkey or not hotkey.strip():
        return False, "Hotkey cannot be empty"
    
    hotkey = hotkey.lower().strip()
    
    # Split by + to check for modifiers
    parts = [part.strip() for part in hotkey.split('+')]
    
    # Check if using invalid regular numbers
    main_key = parts[-1]
    if main_key in INVALID_REGULAR_NUMBERS:
        return False, f"Regular numbers (1-9, 0) are not available. Please use numpad numbers instead (num {main_key})"
    
    # Last part should be a valid hotkey key
    if main_key not in VALID_HOTKEY_KEYS:
        return False, f"Key '{main_key}' is not allowed. Use numpad keys (num 0-9, num *, num /, num .) or allowed letters (p,f,g,h,k,l,z,x,c,v,b,n,m,comma,period,?,',`)"
    
    # All other parts should be modifiers
    for part in parts[:-1]:
        if part not in MODIFIER_KEYS:
            return False, f"'{part}' is not a valid modifier. Use: shift, ctrl, alt"
    
    return True, "Valid hotkey"


def is_valid_hotkey_simple(hotkey: str) -> bool:
    """Simple boolean check for hotkey validity (for backward compatibility)."""
    valid, _ = is_valid_hotkey(hotkey)
    return valid


def is_valid_minigame_value(value_str: str, setting_key: str = None) -> tuple[bool, str]:
    """Validate a minigame setting value.
    
    Args:
        value_str: String representation of the value
        setting_key: Key of the setting being validated (optional, for specific validation rules)
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not value_str or not value_str.strip():
        return False, "Value cannot be empty"
    
    try:
        value = float(value_str.strip())
        
        # Minimum value check - control_value can be 0, others must be at least 0.001
        if setting_key == 'control_value':
            min_value = 0.0
        else:
            min_value = 0.001
            
        if value < min_value:
            return False, f"Value must be at least {min_value} (got {value})"
        
        # Maximum value check - special cases for delay settings
        if setting_key == 'side_bar_delay':
            max_value = 800
        else:
            max_value = 100
            
        if value > max_value:
            return False, f"Value must be at most {max_value} (got {value})"
        else:
            return True, "Valid value"
            
    except ValueError:
        max_val = 800 if setting_key == 'side_bar_delay' else 100
        min_val = "0" if setting_key == 'control_value' else "0.001"
        return False, f"Invalid number format: '{value_str}'. Use numbers like 1.5, 2.001, {max_val} (min: {min_val})"


def is_valid_minigame_value_simple(value_str: str) -> bool:
    """Simple boolean check for minigame value validity."""
    valid, _ = is_valid_minigame_value(value_str)
    return valid


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
        
        # Load settings first
        self.hotkey_settings = load_hotkey_settings()
        self.minigame_settings = load_minigame_settings()
        self.general_settings = load_general_settings()
        
        # Store original settings for change detection
        self.original_hotkey_settings = self.hotkey_settings.copy()
        self.original_minigame_settings = self.minigame_settings.copy()
        self.original_general_settings = self.general_settings.copy()
        
        # Make window stay on top using loaded settings
        self.topmost_enabled = self.general_settings.get('topmost_enabled', True)
        self.attributes('-topmost', self.topmost_enabled)
        self.focus_force()  # Force focus to the window

        self.process = None
        
        # Track if user is typing (to disable hotkeys)
        self.typing_in_field = False
        
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

        # Settings management buttons
        settings_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        settings_frame.pack(pady=(20, 10))

        # Save All Settings button
        save_all_btn = ctk.CTkButton(
            settings_frame,
            text="💾 Save All Settings",
            width=180,
            height=35,
            corner_radius=8,
            fg_color="#28a745",
            hover_color="#218838",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.save_all_settings,
        )
        save_all_btn.pack(side="left", padx=(0, 10))

        # Restore to Default button
        restore_btn = ctk.CTkButton(
            settings_frame,
            text="🔄 Restore to Default",
            width=180,
            height=35,
            corner_radius=8,
            fg_color="#ffc107",
            hover_color="#e0a800",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.restore_to_default,
        )
        restore_btn.pack(side="left", padx=(0, 10))

        # Revert Changes button
        revert_btn = ctk.CTkButton(
            settings_frame,
            text="↩️ Revert Changes",
            width=180,
            height=35,
            corner_radius=8,
            fg_color="#dc3545",
            hover_color="#c82333",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.revert_changes,
        )
        revert_btn.pack(side="left")

        # Changes indicator
        self.changes_label = ctk.CTkLabel(
            tab_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="orange"
        )
        self.changes_label.pack(pady=(10, 0))

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
            text="• Allowed keys: numpad (num 0-9, *, /, .), specific letters (p,f,g,h,k,l,z,x,c,v,b,n,m), symbols (,.'`?)\n• Hotkeys work globally - even when Roblox is focused\n• Entry fields turn GREEN for valid hotkeys, RED for invalid\n• Regular numbers (1-9,0) are blocked to prevent game conflicts\n• Hotkeys are automatically saved when using 'Save All Settings'",
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        instructions_text.pack(padx=20, pady=(0, 10))
        
        # Add hotkey configuration section
        self._add_hotkey_section(scrollable_frame)

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
        
        # Dynamic placeholder text based on setting key
        if key == 'side_bar_delay':
            placeholder_text = f"0.001-800 (e.g., {default_value})"
        elif key == 'control_value':
            placeholder_text = f"0-100 (e.g., {default_value})"
        else:
            placeholder_text = f"0.001-100 (e.g., {default_value})"
        
        entry = ctk.CTkEntry(entry_frame, width=100, placeholder_text=placeholder_text)
        entry.pack(side="right", padx=(10, 0))
        entry.insert(0, str(self.minigame_settings.get(key, default_value)))
        
        # Bind focus events for typing detection, change tracking, and validation
        entry.bind('<FocusIn>', self._on_entry_focus_in)
        entry.bind('<FocusOut>', self._on_entry_focus_out)
        entry.bind('<KeyRelease>', self._on_entry_change)
        
        self.minigame_entries[key] = entry
        
        # Initial validation
        self.after(100, lambda e=entry: self._validate_minigame_entry(e))

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

        # Settings management buttons
        settings_frame = tk.Frame(tab_frame)
        settings_frame.pack(pady=(20, 10))

        # Save All Settings button
        save_all_btn = tk.Button(settings_frame, text="💾 Save All Settings", width=20, height=2, command=self.save_all_settings)
        save_all_btn.pack(side="left", padx=(0, 5))

        # Restore to Default button
        restore_btn = tk.Button(settings_frame, text="🔄 Restore to Default", width=20, height=2, command=self.restore_to_default)
        restore_btn.pack(side="left", padx=(0, 5))

        # Revert Changes button
        revert_btn = tk.Button(settings_frame, text="↩️ Revert Changes", width=20, height=2, command=self.revert_changes)
        revert_btn.pack(side="left")

        # Changes indicator
        self.changes_label = tk.Label(tab_frame, text="", fg="orange")
        self.changes_label.pack(pady=(10, 0))

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
            text="• Allowed keys: numpad (num 0-9,*,/,.), letters (p,f,g,h,k,l,z,x,c,v,b,n,m), symbols (,.'`?)\n• Hotkeys work globally - even when Roblox is focused\n• Entry fields change color: GREEN=valid, RED=invalid\n• Regular numbers (1-9,0) blocked to prevent game conflicts\n• Save hotkeys using 'Save All Settings' button",
            justify="left",
            wraplength=500
        )
        instructions_text.pack()
        
        # Add hotkey configuration section
        self._add_hotkey_section_basic(scrollable_frame)

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
        
        entry = tk.Entry(entry_frame, width=12)
        entry.pack(side="right", padx=(10, 0))
        entry.insert(0, str(self.minigame_settings.get(key, default_value)))
        
        # Bind focus events for typing detection, change tracking, and validation
        entry.bind('<FocusIn>', self._on_entry_focus_in)
        entry.bind('<FocusOut>', self._on_entry_focus_out)
        entry.bind('<KeyRelease>', self._on_entry_change)
        
        self.minigame_entries[key] = entry
        
        # Initial validation
        self.after(100, lambda e=entry: self._validate_minigame_entry(e))

    def _save_minigame_settings(self):
        """Save minigame settings with validation."""
        print("Saving minigame settings with validation...")
        invalid_entries = []
        
        for key, entry in self.minigame_entries.items():
            value = entry.get().strip()
            is_valid, message = is_valid_minigame_value(value, key)
            
            if not is_valid:
                invalid_entries.append(f"{key}: {message}")
            else:
                # Convert to float and store
                try:
                    float_value = float(value)
                    self.minigame_settings[key] = float_value
                except ValueError:
                    invalid_entries.append(f"{key}: Invalid number format")
        
        if invalid_entries:
            error_message = "Invalid minigame values found:\n" + "\n".join(invalid_entries)
            if self.is_modern_ui:
                # Show error dialog for CustomTkinter
                import tkinter.messagebox as messagebox
                messagebox.showerror("Validation Error", error_message)
            else:
                print(f"Validation errors: {error_message}")
            return False
        
        # Save settings to file if all validations pass
        try:
            settings_path = Path("Logic") / "BackGround_Logic" / "settings" / "minigame_settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(settings_path, 'w') as f:
                json.dump(self.minigame_settings, f, indent=4)
            
            # Update any settings that were successfully validated
            self.last_saved_minigame_settings = self.minigame_settings.copy()
            print("Minigame settings saved successfully!")
            return True
            
        except Exception as e:
            error_msg = f"Error saving minigame settings: {e}"
            print(error_msg)
            if self.is_modern_ui:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Save Error", error_msg)
            return False

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

    def save_all_settings(self):
        """Save all settings from GUI to files."""
        try:
            # Update and save hotkey settings
            new_hotkey_settings = {
                'start_hotkey': self.hotkey_entries['start'].get().strip(),
                'stop_hotkey': self.hotkey_entries['stop'].get().strip()
            }
            save_hotkey_settings(new_hotkey_settings)
            self.hotkey_settings = new_hotkey_settings
            self.original_hotkey_settings = new_hotkey_settings.copy()

            # Update and save minigame settings
            new_minigame_settings = {}
            for key, entry in self.minigame_entries.items():
                try:
                    value = entry.get().strip()
                    new_minigame_settings[key] = float(value)
                except ValueError:
                    messagebox.showerror("Invalid Value", f"Invalid value for {key}: '{value}'. Please enter a valid number.")
                    return
            save_minigame_settings(new_minigame_settings)
            self.minigame_settings = new_minigame_settings
            self.original_minigame_settings = new_minigame_settings.copy()

            # Save general settings (topmost, etc.)
            general_settings = {
                'topmost_enabled': self.topmost_enabled,
                'disable_auto_focus': False,  # Removed from UI
                'passive_mode': False  # Removed from UI
            }
            save_general_settings(general_settings)
            self.general_settings = general_settings
            self.original_general_settings = general_settings.copy()

            # Clear changes indicator
            self.update_changes_indicator()

            messagebox.showinfo("Success", "All settings saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")

    def restore_to_default(self):
        """Restore all settings to their defaults."""
        if messagebox.askyesno("Confirm Restore", "Are you sure you want to restore all settings to defaults? This will overwrite all current settings."):
            try:
                # Get default settings
                default_hotkey_settings = {
                    'start_hotkey': 'num 1',
                    'stop_hotkey': 'num 2'
                }
                
                default_minigame_settings = {
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
                
                default_general_settings = {
                    'topmost_enabled': True,
                    'disable_auto_focus': False,
                    'passive_mode': False
                }

                # Update GUI
                self.hotkey_entries['start'].delete(0, tk.END)
                self.hotkey_entries['start'].insert(0, default_hotkey_settings['start_hotkey'])
                self.hotkey_entries['stop'].delete(0, tk.END)
                self.hotkey_entries['stop'].insert(0, default_hotkey_settings['stop_hotkey'])

                for key, entry in self.minigame_entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, str(default_minigame_settings.get(key, 0)))

                # Update topmost
                self.topmost_enabled = default_general_settings['topmost_enabled']
                self.attributes('-topmost', self.topmost_enabled)
                self._update_topmost_button()

                # Save all settings
                save_hotkey_settings(default_hotkey_settings)
                save_minigame_settings(default_minigame_settings)
                save_general_settings(default_general_settings)

                # Update internal state
                self.hotkey_settings = default_hotkey_settings
                self.minigame_settings = default_minigame_settings
                self.general_settings = default_general_settings
                self.original_hotkey_settings = default_hotkey_settings.copy()
                self.original_minigame_settings = default_minigame_settings.copy()
                self.original_general_settings = default_general_settings.copy()

                # Clear changes indicator
                self.update_changes_indicator()

                messagebox.showinfo("Success", "All settings restored to defaults!")

            except Exception as e:
                messagebox.showerror("Error", f"Error restoring settings: {str(e)}")

    def revert_changes(self):
        """Revert all unsaved changes to last saved state."""
        if messagebox.askyesno("Confirm Revert", "Are you sure you want to revert all unsaved changes?"):
            try:
                # Revert hotkey settings
                self.hotkey_entries['start'].delete(0, tk.END)
                self.hotkey_entries['start'].insert(0, self.original_hotkey_settings['start_hotkey'])
                self.hotkey_entries['stop'].delete(0, tk.END)
                self.hotkey_entries['stop'].insert(0, self.original_hotkey_settings['stop_hotkey'])

                # Revert minigame settings
                for key, entry in self.minigame_entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.original_minigame_settings.get(key, 0)))

                # Revert general settings
                self.topmost_enabled = self.original_general_settings.get('topmost_enabled', True)
                self.attributes('-topmost', self.topmost_enabled)
                self._update_topmost_button()

                # Clear changes indicator
                self.update_changes_indicator()

                messagebox.showinfo("Success", "All changes reverted!")

            except Exception as e:
                messagebox.showerror("Error", f"Error reverting changes: {str(e)}")

    def update_changes_indicator(self):
        """Update the changes indicator label."""
        try:
            # Check for changes in hotkey settings
            current_hotkey_settings = {
                'start_hotkey': self.hotkey_entries['start'].get().strip(),
                'stop_hotkey': self.hotkey_entries['stop'].get().strip()
            }
            hotkeys_changed = current_hotkey_settings != self.original_hotkey_settings

            # Check for changes in minigame settings
            current_minigame_settings = {}
            minigame_changed = False
            try:
                for key, entry in self.minigame_entries.items():
                    current_minigame_settings[key] = float(entry.get().strip())
                minigame_changed = current_minigame_settings != self.original_minigame_settings
            except ValueError:
                minigame_changed = True  # Invalid values count as changes

            # Check for changes in general settings
            general_changed = self.topmost_enabled != self.original_general_settings.get('topmost_enabled', True)

            # Update indicator
            if hotkeys_changed or minigame_changed or general_changed:
                self.changes_label.configure(text="⚠️ You have unsaved changes!")
                if hasattr(self.changes_label, 'configure'):
                    if ctk:
                        self.changes_label.configure(text_color="orange")
                    else:
                        self.changes_label.configure(fg="orange")
            else:
                self.changes_label.configure(text="")
        except Exception:
            pass  # Ignore errors in change detection

    def _update_topmost_button(self):
        """Update the topmost button text."""
        status_text = "ON" if self.topmost_enabled else "OFF"
        button_text = f"📌 Always on Top: {status_text}"
        
        if ctk and hasattr(self.topmost_btn, 'configure'):
            self.topmost_btn.configure(text=button_text)
        elif hasattr(self.topmost_btn, 'config'):
            self.topmost_btn.config(text=button_text)

    def _on_entry_focus_in(self, event):
        """Called when user starts typing in an entry field."""
        self.typing_in_field = True

    def _on_entry_focus_out(self, event):
        """Called when user stops typing in an entry field."""
        self.typing_in_field = False

    def _on_entry_change(self, event):
        """Called when user changes text in an entry field."""
        # Update changes indicator when text changes
        self.after(100, self.update_changes_indicator)  # Delay to allow text update
        
        # If this is a hotkey entry, validate and update colors
        widget = event.widget
        if widget in self.hotkey_entries.values():
            self.after(100, lambda: self._validate_hotkey_entry(widget))
        elif widget in self.minigame_entries.values():
            self.after(100, lambda: self._validate_minigame_entry(widget))

    def _validate_hotkey_entry(self, entry_widget):
        """Validate a hotkey entry and update its color."""
        try:
            hotkey_text = entry_widget.get().strip()
            is_valid, message = is_valid_hotkey(hotkey_text)
            
            # Update entry color based on validation
            if ctk and hasattr(entry_widget, 'configure'):
                # CustomTkinter styling
                if is_valid:
                    entry_widget.configure(border_color="green")
                else:
                    entry_widget.configure(border_color="red")
            elif hasattr(entry_widget, 'config'):
                # Regular tkinter styling
                if is_valid:
                    entry_widget.config(bg="lightgreen", fg="black")
                else:
                    entry_widget.config(bg="lightcoral", fg="black")
            
            # Show dialog for invalid regular numbers
            if not is_valid and any(num in hotkey_text for num in INVALID_REGULAR_NUMBERS):
                # Extract the number that was used
                for num in INVALID_REGULAR_NUMBERS:
                    if num in hotkey_text:
                        messagebox.showwarning(
                            "Invalid Hotkey", 
                            f"Regular numbers (1-9, 0) are not available due to game conflicts.\n"
                            f"Please use numpad numbers instead: 'num {num}'"
                        )
                        break
                        
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error validating hotkey: {e}")

    def _validate_minigame_entry(self, entry_widget):
        """Validate a minigame entry and update its color."""
        try:
            value_text = entry_widget.get().strip()
            
            # Find the setting key for this entry
            setting_key = None
            for key, entry in self.minigame_entries.items():
                if entry == entry_widget:
                    setting_key = key
                    break
            
            is_valid, message = is_valid_minigame_value(value_text, setting_key)
            
            # Update entry color based on validation
            if ctk and hasattr(entry_widget, 'configure'):
                # CustomTkinter styling
                if is_valid:
                    entry_widget.configure(border_color="green")
                else:
                    entry_widget.configure(border_color="red")
            elif hasattr(entry_widget, 'config'):
                # Regular tkinter styling
                if is_valid:
                    entry_widget.config(bg="lightgreen", fg="black")
                else:
                    entry_widget.config(bg="lightcoral", fg="black")
                    
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error validating minigame value: {e}")

    def _reset_entry_colors(self):
        """Reset all entry colors to default."""
        try:
            # Reset hotkey entries
            for entry in self.hotkey_entries.values():
                if ctk and hasattr(entry, 'configure'):
                    entry.configure(border_color=None)  # Reset to default
                elif hasattr(entry, 'config'):
                    entry.config(bg="white", fg="black")  # Reset to default
            
            # Reset minigame entries
            for entry in self.minigame_entries.values():
                if ctk and hasattr(entry, 'configure'):
                    entry.configure(border_color=None)  # Reset to default
                elif hasattr(entry, 'config'):
                    entry.config(bg="white", fg="black")  # Reset to default
        except Exception:
            pass

    # status label intentionally removed per user request

    def toggle_topmost(self):
        """Toggle the always-on-top behavior of the window."""
        self.topmost_enabled = not self.topmost_enabled
        self.attributes('-topmost', self.topmost_enabled)
        
        # Update button text and check for changes
        self._update_topmost_button()
        self.update_changes_indicator()

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
            width=150, 
            placeholder_text="e.g., num 1, p, shift+f"
        )
        self.hotkey_entries['start'].pack(side="left", padx=(0, 10))
        self.hotkey_entries['start'].insert(0, self.hotkey_settings['start_hotkey'])
        
        # Bind focus events for typing detection and validation
        self.hotkey_entries['start'].bind('<FocusIn>', self._on_entry_focus_in)
        self.hotkey_entries['start'].bind('<FocusOut>', self._on_entry_focus_out)
        self.hotkey_entries['start'].bind('<KeyRelease>', self._on_entry_change)
        
        # Initial validation
        self.after(100, lambda: self._validate_hotkey_entry(self.hotkey_entries['start']))
        
        # Stop hotkey
        stop_frame = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
        stop_frame.pack(fill="x", padx=10, pady=5)
        
        stop_label = ctk.CTkLabel(stop_frame, text="STOP:", width=60, font=ctk.CTkFont(size=12, weight="bold"))
        stop_label.pack(side="left", padx=(0, 10))
        
        self.hotkey_entries['stop'] = ctk.CTkEntry(
            stop_frame, 
            width=150, 
            placeholder_text="e.g., num 2, g, ctrl+h"
        )
        self.hotkey_entries['stop'].pack(side="left", padx=(0, 10))
        self.hotkey_entries['stop'].insert(0, self.hotkey_settings['stop_hotkey'])
        
        # Bind focus events for typing detection and validation
        self.hotkey_entries['stop'].bind('<FocusIn>', self._on_entry_focus_in)
        self.hotkey_entries['stop'].bind('<FocusOut>', self._on_entry_focus_out)
        self.hotkey_entries['stop'].bind('<KeyRelease>', self._on_entry_change)
        
        # Initial validation
        self.after(100, lambda: self._validate_hotkey_entry(self.hotkey_entries['stop']))
        
        # Info text
        info_text = "Allowed keys: numpad (num 0-9, *, /, .), letters (p,f,g,h,k,l,z,x,c,v,b,n,m), symbols (,.'`?)\nOptional modifiers: shift, ctrl, alt"
        info_label = ctk.CTkLabel(hotkey_frame, text=info_text, font=ctk.CTkFont(size=9), text_color="gray")
        info_label.pack(pady=(10, 10))

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
        
        self.hotkey_entries['start'] = tk.Entry(start_frame, width=25)
        self.hotkey_entries['start'].pack(side="left", padx=(5, 0))
        self.hotkey_entries['start'].insert(0, self.hotkey_settings['start_hotkey'])
        
        # Bind focus events for typing detection and validation
        self.hotkey_entries['start'].bind('<FocusIn>', self._on_entry_focus_in)
        self.hotkey_entries['start'].bind('<FocusOut>', self._on_entry_focus_out)
        self.hotkey_entries['start'].bind('<KeyRelease>', self._on_entry_change)
        
        # Initial validation
        self.after(100, lambda: self._validate_hotkey_entry(self.hotkey_entries['start']))
        
        # Stop hotkey
        stop_frame = tk.Frame(hotkey_frame)
        stop_frame.pack(fill="x", pady=2)
        
        stop_label = tk.Label(stop_frame, text="STOP:", width=8, font=("Segoe UI", 9, "bold"))
        stop_label.pack(side="left")
        
        self.hotkey_entries['stop'] = tk.Entry(stop_frame, width=25)
        self.hotkey_entries['stop'].pack(side="left", padx=(5, 0))
        self.hotkey_entries['stop'].insert(0, self.hotkey_settings['stop_hotkey'])
        
        # Bind focus events for typing detection and validation
        self.hotkey_entries['stop'].bind('<FocusIn>', self._on_entry_focus_in)
        self.hotkey_entries['stop'].bind('<FocusOut>', self._on_entry_focus_out)
        self.hotkey_entries['stop'].bind('<KeyRelease>', self._on_entry_change)
        
        # Initial validation
        self.after(100, lambda: self._validate_hotkey_entry(self.hotkey_entries['stop']))
        
        # Info text
        info_label = tk.Label(hotkey_frame, text="Allowed: numpad (0-9,*,/,.), letters (p,f,g,h,k,l,z,x,c,v,b,n,m), symbols (,.'`?)", 
                             font=("Segoe UI", 8), fg="gray", wraplength=400)
        info_label.pack(pady=(5, 0))

    def _setup_hotkeys(self):
        """Set up hotkey listeners."""
        if not KEYBOARD_AVAILABLE or self.hotkeys_registered:
            return
            
        try:
            # Register hotkeys
            start_hotkey = self.hotkey_settings['start_hotkey']
            stop_hotkey = self.hotkey_settings['stop_hotkey']
            
            if is_valid_hotkey_simple(start_hotkey):
                keyboard.add_hotkey(start_hotkey, self._hotkey_start)
            
            if is_valid_hotkey_simple(stop_hotkey) and start_hotkey != stop_hotkey:
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
            start_valid, start_message = is_valid_hotkey(start_hotkey)
            if not start_valid:
                messagebox.showerror("Invalid Start Hotkey", start_message)
                return
                
            stop_valid, stop_message = is_valid_hotkey(stop_hotkey)
            if not stop_valid:
                messagebox.showerror("Invalid Stop Hotkey", stop_message)
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
            # Don't trigger hotkey if user is typing in a field
            if self.typing_in_field:
                return
                
            # Only start if not already running
            if not self.process or self.process.poll() is not None:
                self.on_start()
        except Exception as e:
            debug_log(LogCategory.ERROR, f"Error in start hotkey: {e}")

    def _hotkey_stop(self):
        """Handle stop hotkey press."""
        try:
            # Don't trigger hotkey if user is typing in a field
            if self.typing_in_field:
                return
                
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
