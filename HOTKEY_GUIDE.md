# Hotkey Guide for Blox Fruit Fishing

## Overview

The Blox Fruit Fishing launcher now supports customizable hotkeys for quick start/stop functionality!

## Default Hotkeys

- **Start Fishing**: `num 1` (Numpad 1)
- **Stop Fishing**: `num 2` (Numpad 2)

## Customizing Hotkeys

### Valid Keys

You can only use **numpad keys** (num 0 through num 9) to avoid conflicts with in-game item hotkeys (1-0 above QWERTYUIOP).

### Valid Numpad Keys

- `num 0`, `num 1`, `num 2`, `num 3`, `num 4`, `num 5`, `num 6`, `num 7`, `num 8`, `num 9`

### Modifiers

You can combine numpad keys with these modifiers:

- `shift` - Shift key
- `ctrl` - Control key  
- `alt` - Alt key

### Examples of Valid Hotkeys

- `num 1` - Just numpad 1
- `shift+num 1` - Shift + numpad 1
- `ctrl+num 5` - Control + numpad 5
- `alt+num 9` - Alt + numpad 9
- `shift+ctrl+num 3` - Shift + Control + numpad 3

### How to Change Hotkeys

1. Open the launcher application
2. Find the "Hotkeys" section in the GUI
3. Enter your desired hotkey in the text boxes next to "START:" and "STOP:"
4. Click "Apply Hotkeys"
5. A success message will confirm the hotkeys are updated

### Rules

- Start and stop hotkeys must be different
- Only numpad keys are allowed (to avoid game conflicts)
- Modifiers are optional but recommended for complex setups
- Hotkeys work globally (even when the launcher is minimized)

## Troubleshooting

### Hotkeys Not Working?

1. Make sure you're using numpad keys, not the number row above letters
2. Check that the `keyboard` library is installed: `pip install keyboard`
3. Verify your hotkeys are valid using the examples above
4. Try running the launcher as administrator if needed

### Invalid Hotkey Error?

- Make sure you're using the format: `modifier+num X` (e.g., `shift+num 1`)
- Don't use spaces around the `+` symbol
- Only use numpad keys (num 0-9)
- Only use valid modifiers (shift, ctrl, alt)

## Settings Storage

Your hotkey preferences are automatically saved in `hotkey_settings.json` and will be remembered between sessions.

## Why Numpad Only?

The regular number keys (1, 2, 3, etc. above QWERTY) are reserved for equipping in-game items in Roblox/Blox Fruits. Using numpad keys ensures no conflicts with game functionality.
