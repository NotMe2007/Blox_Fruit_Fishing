# Blox Fruit Fishing Macro - AI Coding Instructions

## Architecture Overview

This is a Roblox game automation tool with a **launcher-script separation pattern**:
- `Main.py`: GUI launcher with hotkey management and Roblox validation  
- `Logic/fishing_Script.py`: Core automation engine with template matching
- `Logic/BackGround_Logic/`: Specialized detection and control modules

**Process Communication**: Launcher spawns script via `subprocess.Popen()` with daemon threading for non-blocking execution. No IPC - script runs independently once launched.

**UI Flexibility**: Runtime detection of `customtkinter` availability with `tkinter` fallback using dynamic base class assignment pattern.

**Import Strategy**: All modules use defensive imports with availability flags (`VIRTUAL_MOUSE_AVAILABLE`, `FISHING_ROD_DETECTOR_AVAILABLE`) allowing graceful degradation when dependencies missing.

## Key Patterns & Conventions

### Defensive Import Pattern (CRITICAL)
All BackGround_Logic modules follow this dual-import strategy:
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
        # Always provide fallback behavior/dummy functions
```

### Template Matching System
All visual detection uses OpenCV template matching with consistent patterns:
```python
template = safe_load_template(IMAGES_DIR / 'template_name.png')
found, score = _match_template_in_region(template, region, threshold=0.80)
```
- Templates stored in `Images/` directory (PNG/JPG files)
- Always implement fallback detection when templates fail
- Use grayscale conversion for better matching reliability  
- Debug images saved as `debug_*.png` when debugging enabled

### Debug Logger System
Use centralized logging with selective categories:
```python
from BackGround_Logic.Debug_Logger import debug_log, LogCategory
debug_log(LogCategory.FISH_DETECTION, "Template match score: 0.85")
```
- Categories: `SYSTEM`, `FISH_DETECTION`, `MINIGAME`, `ERROR`, `MOUSE`, etc.
- Enable/disable categories for cleaner testing output
- Emoji indicators for visual category recognition

### Anti-Detection Input Simulation
- **Virtual Mouse**: `Virtual_Mouse.py` uses Windows API calls, not PyAutoGUI
- **Randomization**: `offset_x = random.randint(-2, 2)` for click positions
- **Human Timing**: `time.sleep(random.uniform(0.05, 0.15))` between actions
- **Hardware-Level**: Virtual mouse driver bypasses userland detection

### Configuration Management
- **JSON Settings**: Hotkeys in `Logic/BackGround_Logic/hotkey_settings.json`; all configs stay human-readable, JSON-based, and are expected to be edited at runtime before being persisted back to disk
- **Numpad Restriction**: `VALID_NUMPAD_KEYS = ['num 0', 'num 1', ...]` (avoids game conflicts)
- **Dataclass Configs**: `MinigameConfig` uses `@dataclass` for structured parameters
- **Runtime Settings**: Settings loaded/saved dynamically during execution

### Minigame Control Logic  
- **Physics-Based**: `Fishing_Mini_Game.py` implements ported AutoHotkey fishing logic
- **Action System**: 7 action types (0=stabilize, 1-2=stable tracking, 3-4=boundary correction, 5-6=unstable movement)
- **Normalized Coordinates**: All positions use 0-1 range for resolution independence
- **Decision Engine**: `MinigameController.decide()` returns action dicts with intensity/duration

## Development Workflows

### Running/Testing
1. **Quick Setup**: `Run_Me.bat` handles Python install, deps, and launch
2. **Manual Launch**: `python Main.py` (validates Roblox state first)
3. **Quick Testing**: `python tests/quick_test.py` for essential functionality
4. **Full Testing**: `python tests/run_all_tests.py` for comprehensive validation

### Adding New Detection Features
1. Add template images to `Images/` directory
2. Use `safe_load_template()` helper for image loading
3. Implement defensive imports with availability flags
4. Test threshold values between 0.55-0.85 for template matching
5. Add debug logging with appropriate `LogCategory`

### Hotkey System Extension
- Modify `VALID_NUMPAD_KEYS` in `Main.py`
- Update `hotkey_settings.json` structure
- Add handlers following `_hotkey_start()` pattern
- Use daemon threads for non-blocking execution

### Module Development
- Always implement the defensive import pattern
- Set availability flags for graceful degradation
- Use centralized debug logger with appropriate categories
- Add fallback dummy functions when imports fail
- Test both package-relative and absolute import scenarios

## Critical Dependencies
- `customtkinter>=5.2.2`: Modern UI (fallback to `tkinter`)
- `opencv-python`: Template matching engine
- `pywin32`: Windows API access for undetectable input
- `numpy`: Numerical operations for image processing
- `psutil`: Process detection and management
- `keyboard`: Global hotkey system (optional)

## File Structure Notes
- `BackGround_Logic/` contains all detection/control modules
- `Logic/` contains main automation logic
- Templates in `Images/` with descriptive names (`Fish_On_Hook.png`, `MiniGame_Bar.png`)
- Debug output saved to `debug/` directory
- Tests in `tests/` with modular structure for each component
- JSON configs for runtime settings (hotkeys, minigame parameters)

