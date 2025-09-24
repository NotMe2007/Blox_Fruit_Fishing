# Blox Fruit Fishing Macro - AI Coding Instructions

## Architecture Overview

This is a Roblox game automation tool with a **launcher-script separation pattern**:
- `Main.py`: GUI launcher with hotkey management and Roblox validation
- `Logic/fishing_Script.py`: Core automation engine with template matching  
- `Logic/BackGroud_Logic/`: Specialized detection and control modules

**Process Communication**: Launcher spawns script via `subprocess.Popen()` with daemon threading for non-blocking execution. No IPC - script runs independently once launched.

**UI Flexibility**: Runtime detection of `customtkinter` availability with `tkinter` fallback using dynamic base class assignment (`_BaseClass = ctk.CTk if ctk else tk.Tk`)

**Import Strategy**: All modules use defensive imports with availability flags (`VIRTUAL_MOUSE_AVAILABLE`, `FISHING_ROD_DETECTOR_AVAILABLE`) allowing graceful degradation when dependencies missing

## Key Patterns & Conventions

### Template Matching System
All visual detection uses OpenCV template matching with fallback patterns:
```python
# Standard pattern in all detector modules
template = safe_load_template(IMAGES_DIR / 'template_name.png')
found, score = _match_template_in_region(template, region, threshold=0.80)
```
- Templates stored in `Images/` directory (PNG/JPG files)
- Always implement fallback detection when templates fail
- Use grayscale conversion for better matching reliability
- Debug images saved as `debug_*.png` when debugging enabled

### Dual Import Pattern
All BackGround_Logic modules follow this defensive import strategy:
```python
try:
    from .ModuleName import ClassName  # Package-relative import
    MODULE_AVAILABLE = True
except ImportError:
    try:
        from ModuleName import ClassName  # Absolute fallback
        MODULE_AVAILABLE = True
    except ImportError:
        MODULE_AVAILABLE = False
```

### Roblox Integration Points
- **Game State Detection**: `Is_Roblox_Open.py` uses both process detection AND Roblox API calls
- **Window Management**: `Window_Manager.py` finds Roblox windows by title matching "blox fruits"
- **Input Simulation**: `Virtual_Mouse.py` uses low-level Windows API to avoid detection
- **Coordinate System**: All coordinates are normalized to screen regions for multi-resolution support

### Minigame Control Logic
- **Physics-Based**: `Fishing_Mini_Game.py` implements ported AutoHotkey fishing logic
- **Decision System**: `MinigameController.decide()` returns action dictionaries with intensity/duration
- **Normalized Coordinates**: All positions use 0-1 range (0=left, 1=right) for resolution independence  
- **State Inputs**: indicator position, arrow direction, stability flag drive decision logic

### Configuration Management  
- **Dataclass Configs**: `MinigameConfig` uses `@dataclass` for structured parameters
- **JSON Settings**: Hotkeys in `Logic/BackGround_Logic/hotkey_settings.json`
- **Numpad Restriction**: Only numpad keys allowed (avoids game item hotkey conflicts)
- **Validation Pattern**: `VALID_NUMPAD_KEYS = [f"num {i}" for i in range(10)]`
- **Threading**: Launcher uses daemon threads for non-blocking script execution

### Error Handling Strategy
- Template loading failures set variables to `None` rather than crashing
- API failures fall back to process/window title detection
- All external calls wrapped in try-catch with graceful degradation

### Module Availability Pattern
Each module sets availability flags to handle missing dependencies:
```python
try:
    from BackGround_Logic.Virtual_Mouse import VirtualMouse
    virtual_mouse = VirtualMouse()
    VIRTUAL_MOUSE_AVAILABLE = True
except ImportError:
    virtual_mouse = None  
    VIRTUAL_MOUSE_AVAILABLE = False
```

## Development Workflows

### Adding New Templates
1. Add image to `Images/` directory
2. Use `safe_load_template()` helper in detector modules
3. Implement fallback detection method
4. Test with `threshold` values between 0.55-0.85

### Hotkey System Extension
- Modify `VALID_NUMPAD_KEYS` in `Main.py`
- Update `hotkey_settings.json` structure
- Add handlers following `_hotkey_start()` pattern

### Testing Automation Features
- Run `Main.py` first (validates Roblox state)
- Use `debug=True` in detector modules for visual feedback
- Template matching debug images saved as `debug_*.png`

## Critical Dependencies
- `customtkinter`: Modern UI components (fallback to `tkinter`)
- `opencv-python`: Template matching engine
- `pyautogui`/`VirtualMouse`: Input simulation with anti-detection
- `psutil`/`win32gui`: Process and window management
- `keyboard`: Global hotkey system (optional)

## Anti-Detection Measures
- Random click offsets: `offset_x = random.randint(-2, 2)`
- Variable timing: `time.sleep(random.uniform(0.05, 0.15))`
- Human-like mouse movements via `smooth_move_to()`
- Virtual mouse driver bypasses userland detection

