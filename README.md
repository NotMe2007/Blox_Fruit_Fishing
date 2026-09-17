# Blox Fruit Fishing

Windows fishing automation for Blox Fruits with rod detection and configurable hotkeys.

## Setup

On Windows, opening `Run_Me.bat`, `Launcher.py`, `Main.py`, or the rebuilt
`dist/Launcher.exe` requests administrator access through the standard UAC
prompt. Accept it to start. Cancelling exits without starting the bot. Already
elevated launches continue without another prompt.

Install Python 3.10 or newer, then double-click Run_Me.bat. Both launch paths now
use Launcher.py. A local .venv is preferred when available. You can also install
requirements.txt and run Main.py directly. Git checkouts skip automatic release
replacement to preserve local changes.

Keep Roblox visible, unobscured, and fully on screen, with the basic rod in the
hotbar. Default hotkeys: numpad 1 starts and numpad 2 stops.

## Detection

The rod search follows the central 60% of the bottom 15% of the current client
area, accounting for movement, resizing, and Windows display scaling. Capture
supports negative coordinates on secondary monitors. Templates are matched at
50–200% size. Only the bundled basic rod appearances are supported.

Inspect debug/rod_detection_region.png and the UN/EQ confidence logs if detection
fails. Capture failures and missing templates leave the rod state unknown.
Live gameplay and mixed-DPI input still require verification with Roblox.

## Updates

Numeric version comparison ignores V/v prefixes and prevents downgrades.
Extracted releases receive their actual tag in version.txt before testing or
installation, preventing repeat updates from stale version files. Existing
executable builds need rebuilding; use Run_Me.bat or Launcher.py for these fixes.

## Regression tests

Install pytest, then run:

    python -m pytest tests/test_camera_input.py tests/test_mouse_input.py tests/test_regressions.py tests/test_fishing_rod_detector.py -q

These tests simulate windows and images without sending input. Older diagnostic
scripts in tests may interact with the desktop.

## Mouse input

Mouse clicks, casting holds, and minigame button events use Windows SendInput.
The previous PostMessage path only confirmed queueing a window message. The new
path checks how many input events Windows accepted and reports failures.
Keep Roblox in the foreground: presses outside its client or while another app
is active are skipped. Button releases still run after focus loss or an interrupted
click hold. Run Roblox and the launcher at the same privilege level; SendInput is
subject to Windows integrity restrictions. An accepted event does not prove that
the game acted on it and is not an anti-cheat bypass.

Restart the running bot with Run_Me.bat to load these source changes. The startup
log should say: Mouse backend: Windows SendInput (foreground input).

Camera setup also uses SendInput: scan-code I/O key presses with the full Win32
INPUT structure and relative right-button dragging for cursor-locked games.
Keyboard startup should say "Keyboard backend: Windows SendInput scan codes".
Input failures stop camera setup instead of silently continuing. Equipped rod
recognition requires the cyan selection border; matching the rod icon alone is
not sufficient. These are compatibility fixes, not evidence that a live game
accepted the input. The keyboard implementation follows Microsoft's KEYBDINPUT
and SendInput documentation.

Casting uses a 220 ms smooth cursor glide, a 150 ms settling pause, and
button-only down/up events around the hold. It logs whether Windows reports
the left button held and whether release was accepted. A missing held state
returns failure instead of entering the fish-wait state.

## Runtime recovery

The loop confirms equipment with read-only observations. It sends at most one
hotbar click while equipping and never clicks during confirmation or centering.
An uncertain meter observation does not trigger an immediate rod reset: accepted
cast input proceeds to the bite-wait state. Only a full 60-second bite timeout
allows an intentional unequip/re-equip cycle, with at most two resets before
stopping. Input failures stop without toggling the rod. This avoids cancelling a
valid cast when the meter detector misses a frame.

Runtime regressions: run tests/test_runtime_loop.py with pytest. These drive the
actual main loop using a simulated clock and game observations.

Hotbar clicks and casting glide to their target over about 220 ms, then wait
150 ms before pressing. The button-down event contains no movement, allowing
the game to update which UI element is under the cursor first. Failed movement
or lost focus prevents the click. Camera dragging and minigame control retain
their existing timing.
