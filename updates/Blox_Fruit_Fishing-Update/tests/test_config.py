"""
Test Configuration and Utilities

Shared utilities and configuration for all test modules.
"""

import sys
import os
from pathlib import Path
import time

# Project structure
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
LOGIC_DIR = PROJECT_ROOT / "Logic"
BACKGROUND_LOGIC_DIR = LOGIC_DIR / "BackGround_Logic"
IMAGES_DIR = PROJECT_ROOT / "Images"

# Add paths for imports
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(LOGIC_DIR))
sys.path.insert(0, str(BACKGROUND_LOGIC_DIR))

def print_test_header(test_name, description=""):
    """Print a formatted test header."""
    print("=" * 60)
    print(f"🧪 {test_name}")
    if description:
        print(f"📝 {description}")
    print("=" * 60)
    print()

def print_test_section(section_name):
    """Print a test section separator."""
    print(f"🔍 {section_name}")
    print("-" * 40)

def print_test_result(test_name, success, details=""):
    """Print a standardized test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   📋 {details}")

def print_test_warning(test_name, details=""):
    """Print a test warning."""
    print(f"⚠️ WARNING {test_name}")
    if details:
        print(f"   📋 {details}")

def print_test_info(message):
    """Print informational message."""
    print(f"💡 {message}")

def time_test(func):
    """Decorator to time test execution."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        print(f"⏱️ Test completed in {duration:.2f}s")
        return result
    return wrapper

def safe_import(module_path, item_name=None):
    """Safely import a module or item from a module."""
    try:
        if item_name:
            module = __import__(module_path, fromlist=[item_name])
            return getattr(module, item_name), True
        else:
            return __import__(module_path), True
    except ImportError as e:
        return None, False
    except Exception as e:
        return None, False

def check_file_exists(file_path, description=""):
    """Check if a file exists and print result."""
    if file_path.exists():
        print_test_result(f"File exists: {file_path.name}", True, description)
        return True
    else:
        print_test_result(f"File missing: {file_path.name}", False, description)
        return False

def check_directory_exists(dir_path, description=""):
    """Check if a directory exists and print result."""
    if dir_path.exists() and dir_path.is_dir():
        print_test_result(f"Directory exists: {dir_path.name}", True, description)
        return True
    else:
        print_test_result(f"Directory missing: {dir_path.name}", False, description)
        return False

def summarize_test_results(test_name, passed, total, warnings=0):
    """Print a test summary."""
    print()
    print("📊 TEST SUMMARY")
    print("-" * 30)
    print(f"Test Suite: {test_name}")
    print(f"Passed: {passed}/{total}")
    
    if warnings > 0:
        print(f"Warnings: {warnings}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        status = "success"
    elif passed >= total - (total // 4):  # Allow 25% failure rate
        print("✅ MOSTLY WORKING")
        status = "partial"
    else:
        print("❌ MULTIPLE FAILURES")
        status = "failure"
    
    print()
    return status

def get_test_files():
    """Get all available test files."""
    test_files = []
    
    possible_tests = [
        "test_imports.py",
        "test_debug_logger.py",
        "test_virtual_mouse.py", 
        "test_window_manager.py",
        "test_fishing_script.py"
    ]
    
    for test_file in possible_tests:
        test_path = TESTS_DIR / test_file
        if test_path.exists():
            test_files.append(test_path)
    
    return test_files

# Template files that should exist
REQUIRED_TEMPLATES = [
    "Fish_On_Hook.png",
    "Fish_Left.png", 
    "Fish_Right.png",
    "MiniGame_Bar.png",
    "Basic_Fishing_EQ.png",
    "Basic_Fishing_UN.png"
]

OPTIONAL_TEMPLATES = [
    "Power_Active.png",
    "Power_Max.png",
    "Shift_Lock.png",
    "Sunken_Chest.png",
    "GodHuman.png"
]

# Core dependencies that should be available
CORE_DEPENDENCIES = [
    "cv2",           # OpenCV for template matching
    "numpy",         # Numerical operations
    "PIL",           # Image processing
    "psutil",        # Process management
    "win32gui",      # Windows API (optional)
    "keyboard"       # Keyboard input (optional)
]

# Project modules that should import successfully  
PROJECT_MODULES = [
    "Main",
    "Logic.Fishing_Script",
    "Logic.BackGround_Logic.Virtual_Mouse",
    "Logic.BackGround_Logic.Window_Manager",
    "Logic.BackGround_Logic.Is_Roblox_Open"
]