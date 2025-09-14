import os
import sys
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as messagebox

try:
    import customtkinter as ctk
except Exception:
    ctk = None

# Import the Roblox checker
from Logic.IsRoblox_Open import check_roblox_and_game


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "Logic", "Fishing_Script.py")


def resource_exists(path: str) -> bool:
    return os.path.isfile(path)


# determine the base class at runtime to ensure a proper class object is used
_BaseClass = ctk.CTk if ctk else tk.Tk

class _BaseLauncher(_BaseClass):
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
        width, height = 520, 340
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

        hint = ctk.CTkLabel(container, text="Tip: Keep the game window open. Click again to stop the script.")
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
        from Logic.IsRoblox_Open import RobloxChecker
        
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



if __name__ == "__main__":
    # Don't print noisy messages on startup; GUI will fall back to tkinter automatically
    app = LauncherApp()
    app.mainloop()
