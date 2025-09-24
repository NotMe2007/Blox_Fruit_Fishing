"""
Virtual Keyboard Driver using Windows API for undetectable keyboard input.
Uses low-level Windows API calls to simulate hardware keyboard input.
"""
import ctypes
import ctypes.wintypes
import time
from typing import Dict, Optional, Union


# Windows API constants for keyboard
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

INPUT_KEYBOARD = 1
HC_ACTION = 0

# Virtual key codes for common keys
VK_CODES = {
    # Letters
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    
    # Numbers
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    
    # Function keys
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B,
    
    # Numpad
    'num0': 0x60, 'num1': 0x61, 'num2': 0x62, 'num3': 0x63, 'num4': 0x64,
    'num5': 0x65, 'num6': 0x66, 'num7': 0x67, 'num8': 0x68, 'num9': 0x69,
    'multiply': 0x6A, 'add': 0x6B, 'separator': 0x6C, 'subtract': 0x6D,
    'decimal': 0x6E, 'divide': 0x6F,
    
    # Arrow keys
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    
    # Common keys
    'space': 0x20, 'enter': 0x0D, 'return': 0x0D, 'tab': 0x09,
    'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12, 'esc': 0x1B, 'escape': 0x1B,
    'backspace': 0x08, 'delete': 0x2E, 'insert': 0x2D,
    'home': 0x24, 'end': 0x23, 'pageup': 0x21, 'pagedown': 0x22,
    
    # Modifier keys
    'lshift': 0xA0, 'rshift': 0xA1, 'lctrl': 0xA2, 'rctrl': 0xA3,
    'lalt': 0xA4, 'ralt': 0xA5, 'lwin': 0x5B, 'rwin': 0x5C,
    
    # Lock keys
    'capslock': 0x14, 'numlock': 0x90, 'scrolllock': 0x91,
    
    # Special characters (require shift for symbols)
    '!': 0x31, '@': 0x32, '#': 0x33, '$': 0x34, '%': 0x35,
    '^': 0x36, '&': 0x37, '*': 0x38, '(': 0x39, ')': 0x30,
}

# Windows API structures
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT)
    ]


class VirtualKeyboard:
    """
    Virtual keyboard driver that uses Windows API to create hardware-level keyboard input.
    Bypasses most detection methods by simulating actual hardware input events.
    """
    
    def __init__(self):
        """Initialize the virtual keyboard driver."""
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Verify API availability
        try:
            self.user32.SendInput.argtypes = [
                ctypes.wintypes.UINT,
                ctypes.POINTER(INPUT),
                ctypes.c_int
            ]
            self.user32.SendInput.restype = ctypes.wintypes.UINT
            print("Virtual keyboard initialized successfully")
        except Exception as e:
            print(f"Warning: Virtual keyboard initialization failed: {e}")
    
    def _create_keyboard_input(self, vk_code: int, flags: int) -> INPUT:
        """Create a keyboard input structure."""
        input_struct = INPUT()
        input_struct.type = INPUT_KEYBOARD
        input_struct.ki.wVk = vk_code
        input_struct.ki.wScan = 0
        input_struct.ki.dwFlags = flags
        input_struct.ki.time = 0
        input_struct.ki.dwExtraInfo = None
        return input_struct
    
    def _send_input(self, input_struct: INPUT) -> bool:
        """Send input to the system."""
        try:
            result = self.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
            return result == 1
        except Exception as e:
            print(f"Error sending keyboard input: {e}")
            return False
    
    def _get_vk_code(self, key: Union[str, int]) -> Optional[int]:
        """Get virtual key code from key name or return the code if already int."""
        if isinstance(key, int):
            return key
        
        key_str = str(key).lower()
        return VK_CODES.get(key_str)
    
    def key_down(self, key: Union[str, int]) -> bool:
        """Press a key down (without releasing)."""
        vk_code = self._get_vk_code(key)
        if vk_code is None:
            print(f"Unknown key: {key}")
            return False
        
        key_input = self._create_keyboard_input(vk_code, KEYEVENTF_KEYDOWN)
        return self._send_input(key_input)
    
    def key_up(self, key: Union[str, int]) -> bool:
        """Release a key."""
        vk_code = self._get_vk_code(key)
        if vk_code is None:
            print(f"Unknown key: {key}")
            return False
        
        key_input = self._create_keyboard_input(vk_code, KEYEVENTF_KEYUP)
        return self._send_input(key_input)
    
    def key_press(self, key: Union[str, int], duration: float = 0.05) -> bool:
        """Press and release a key with specified duration."""
        success = self.key_down(key)
        if success:
            time.sleep(duration)
            success = self.key_up(key)
        return success
    
    def key_combination(self, *keys, duration: float = 0.05) -> bool:
        """Press multiple keys simultaneously (like Ctrl+C)."""
        # Press all keys down
        for key in keys:
            if not self.key_down(key):
                # If any key fails, release all previously pressed keys
                for prev_key in keys[:keys.index(key)]:
                    self.key_up(prev_key)
                return False
        
        # Hold for duration
        time.sleep(duration)
        
        # Release all keys (in reverse order)
        success = True
        for key in reversed(keys):
            if not self.key_up(key):
                success = False
        
        return success
    
    def type_text(self, text: str, delay: float = 0.05) -> bool:
        """Type text character by character."""
        success = True
        for char in text:
            if char == ' ':
                if not self.key_press('space', delay):
                    success = False
            elif char.isupper():
                # Handle uppercase letters with shift
                if not self.key_combination('shift', char.lower(), duration=delay):
                    success = False
            elif char in VK_CODES:
                if not self.key_press(char, delay):
                    success = False
            else:
                print(f"Warning: Cannot type character '{char}'")
                success = False
            
            # Small delay between characters for more natural typing
            time.sleep(delay * 0.5)
        
        return success
    
    def hold_key(self, key: Union[str, int], duration: float) -> bool:
        """Hold a key down for specified duration."""
        success = self.key_down(key)
        if success:
            time.sleep(duration)
            success = self.key_up(key)
        return success
    
    def tap_key_multiple(self, key: Union[str, int], count: int, delay: float = 0.1) -> bool:
        """Tap a key multiple times with delay between presses."""
        success = True
        for i in range(count):
            if not self.key_press(key, 0.05):
                success = False
            if i < count - 1:  # Don't delay after the last press
                time.sleep(delay)
        return success
    
    def is_key_available(self, key: Union[str, int]) -> bool:
        """Check if a key is available/supported."""
        return self._get_vk_code(key) is not None
    
    def get_available_keys(self) -> Dict[str, int]:
        """Get dictionary of all available keys and their VK codes."""
        return VK_CODES.copy()


# Global instance for easy access
virtual_keyboard = VirtualKeyboard()


# Convenience functions for common operations
def press_key(key: Union[str, int], duration: float = 0.05) -> bool:
    """Press a key using the global virtual keyboard instance."""
    return virtual_keyboard.key_press(key, duration)

def hold_key(key: Union[str, int], duration: float) -> bool:
    """Hold a key using the global virtual keyboard instance."""
    return virtual_keyboard.hold_key(key, duration)

def key_combo(*keys, duration: float = 0.05) -> bool:
    """Press key combination using the global virtual keyboard instance."""
    return virtual_keyboard.key_combination(*keys, duration=duration)

def type_text(text: str, delay: float = 0.05) -> bool:
    """Type text using the global virtual keyboard instance."""
    return virtual_keyboard.type_text(text, delay)


if __name__ == "__main__":
    # Test the virtual keyboard
    print("Testing Virtual Keyboard...")
    
    # Test single key press
    print("Testing key press...")
    time.sleep(2)
    virtual_keyboard.key_press('a')
    
    # Test key combination
    print("Testing key combination (Ctrl+A)...")
    time.sleep(1)
    virtual_keyboard.key_combination('ctrl', 'a')
    
    # Test typing
    print("Testing text typing...")
    time.sleep(1)
    virtual_keyboard.type_text("Hello World!")
    
    print("Virtual Keyboard test completed!")