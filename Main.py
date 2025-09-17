import os
import sys
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as messagebox
import json
from typing import Dict, Optional

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("Warning: keyboard library not available. Hotkeys will not work.")

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except Exception:
    CTK_AVAILABLE = False
    ctk = None

# Import the Roblox checker
from Logic.BackGroud_Logic.IsRoblox_Open import check_roblox_and_game


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "Logic", "Fishing_Script.py")
SETTINGS_FILE = os.path.join(BASE_DIR, "Logic", "BackGroud_Logic", "hotkey_settings.json")

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
        print(f"Error loading hotkey settings: {e}")
    
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
        print(f"Error saving hotkey settings: {e}")


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
        width, height = 650, 480  # Increased height for hotkey settings
        # center window on screen
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        
        # Make window stay on top
        self.attributes('-topmost', True)
        self.focus_force()  # Force focus to the window
        self.topmost_enabled = True

        self.process = None
        
        # Load hotkey settings
        self.hotkey_settings = load_hotkey_settings()
        self.hotkeys_registered = False
        self.hotkey_entries = {}  # Store hotkey entry widgets
        
        # Initialize hotkeys if keyboard library is available
        if KEYBOARD_AVAILABLE:
            self._setup_hotkeys()

        if ctk:
            self._build_modern_ui()
        else:
            self._build_basic_ui()

    def _build_modern_ui(self):
        # container frame
        container = ctk.CTkFrame(self, corner_radius=18)
        container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.92)

        title = ctk.CTkLabel(container, text="Auto Fishing", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(pady=(18, 6))

        subtitle = ctk.CTkLabel(container, text="Launch the automated fishing script", font=ctk.CTkFont(size=12))
        subtitle.pack(pady=(0, 18))

        self.btn = ctk.CTkButton(
            container,
            text="Auto Fishing",
            width=260,
            height=70,
            corner_radius=14,
            fg_color="#1fb57a",
            hover_color="#199a63",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.on_start,
        )
        self.btn.pack(pady=(0, 12))


        # Add topmost toggle button
        self.topmost_btn = ctk.CTkButton(
            container,
            text="📌 Always on Top: ON",
            width=200,
            height=25,
            corner_radius=8,
            fg_color="#444444",
            hover_color="#555555",
            font=ctk.CTkFont(size=11),
            command=self.toggle_topmost,
        )
        self.topmost_btn.pack(pady=(6, 6))

        # Add hotkey configuration section
        self._add_hotkey_section(container)
        
        hint = ctk.CTkLabel(container, text="Tip: Keep the game window open. Use hotkeys for quick start/stop.")
        hint.pack(side="bottom", pady=(6, 12))

    def _build_basic_ui(self):
        # fallback if customtkinter is not installed
        frame = tk.Frame(self, bd=2, relief="groove")
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.92)

        title = tk.Label(frame, text="Auto Fishing", font=("Segoe UI", 20, "bold"))
        title.pack(pady=(14, 6))

        subtitle = tk.Label(frame, text="Launch the automated fishing script")
        subtitle.pack(pady=(0, 12))

        self.btn = tk.Button(frame, text="Auto Fishing", width=30, height=2, command=self.on_start)
        self.btn.pack(pady=(0, 8))
        
        # Add topmost toggle button for basic UI
        self.topmost_btn = tk.Button(frame, text="📌 Always on Top: ON", width=25, height=1, command=self.toggle_topmost)
        self.topmost_btn.pack(pady=(4, 4))
        
        # Add hotkey configuration section for basic UI
        self._add_hotkey_section_basic(frame)

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
            print("Starting fishing script...")
            
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
        from Logic.BackGroud_Logic.IsRoblox_Open import RobloxChecker
        
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
            print(f"Hotkeys registered: Start={start_hotkey}, Stop={stop_hotkey}")
            
        except Exception as e:
            print(f"Error setting up hotkeys: {e}")

    def _clear_hotkeys(self):
        """Clear all registered hotkeys."""
        if not KEYBOARD_AVAILABLE or not self.hotkeys_registered:
            return
            
        try:
            keyboard.clear_all_hotkeys()
            self.hotkeys_registered = False
            print("All hotkeys cleared")
        except Exception as e:
            print(f"Error clearing hotkeys: {e}")

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
            print(f"Error in start hotkey: {e}")

    def _hotkey_stop(self):
        """Handle stop hotkey press."""
        try:
            # Only stop if currently running
            if self.process and self.process.poll() is None:
                self._stop_process()
        except Exception as e:
            print(f"Error in stop hotkey: {e}")

    def destroy(self):
        """Clean up hotkeys when closing the application."""
        self._clear_hotkeys()
        super().destroy()



if __name__ == "__main__":
    # Don't print noisy messages on startup; GUI will fall back to tkinter automatically
    app = LauncherApp()
    app.mainloop()
