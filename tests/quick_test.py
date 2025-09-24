"""
Quick Test Runner

A simple script to quickly test the most essential functionality.
This is a lightweight alternative to the full test suite.
"""

from test_config import *
import traceback

def quick_import_test():
    """Quick test of essential imports."""
    print_test_section("Essential Import Test")
    
    essential_imports = [
        ("cv2", "OpenCV for template matching"),
        ("numpy", "Numerical operations"), 
        ("PIL", "Image processing"),
        ("Main", "Main launcher script"),
    ]
    
    passed = 0
    total = len(essential_imports)
    
    for module_name, description in essential_imports:
        try:
            __import__(module_name)
            print_test_result(f"{module_name}", True, description)
            passed += 1
        except ImportError:
            print_test_result(f"{module_name}", False, f"{description} - Missing")
        except Exception as e:
            print_test_result(f"{module_name}", False, f"{description} - Error: {e}")
    
    return passed, total

def quick_file_test():
    """Quick test of essential files."""
    print_test_section("Essential File Test")
    
    essential_files = [
        (PROJECT_ROOT / "Main.py", "GUI launcher"),
        (LOGIC_DIR / "Fishing_Script.py", "Core automation script"),
        (IMAGES_DIR / "Fish_On_Hook.png", "Fish detection template"),
        (IMAGES_DIR / "MiniGame_Bar.png", "Minigame template")
    ]
    
    passed = 0
    total = len(essential_files)
    
    for file_path, description in essential_files:
        if check_file_exists(file_path, description):
            passed += 1
    
    return passed, total

def quick_dependency_test():
    """Quick test of key dependencies."""
    print_test_section("Key Dependency Test")
    
    passed = 0
    total = 0
    
    # Test OpenCV functionality
    try:
        import cv2
        import numpy as np
        
        # Test basic OpenCV operations
        test_img = np.zeros((10, 10), dtype=np.uint8)
        cv2.matchTemplate(test_img, test_img, cv2.TM_CCOEFF_NORMED)
        
        print_test_result("OpenCV template matching", True)
        passed += 1
    except Exception as e:
        print_test_result("OpenCV template matching", False, str(e))
    total += 1
    
    # Test Windows API
    try:
        import win32gui
        # Test getting desktop window
        win32gui.GetDesktopWindow()
        print_test_result("Windows API access", True)
        passed += 1
    except Exception as e:
        print_test_result("Windows API access", False, "Optional - may work with pyautogui")
        # Don't count as failure since it's optional
    total += 1
    
    return passed, total

def quick_project_test():
    """Quick test of project structure."""
    print_test_section("Project Structure Test")
    
    passed = 0
    total = 0
    
    # Test debug logger
    try:
        from Logic.BackGround_Logic.Debug_Logger import debug_log, LogCategory
        debug_log(LogCategory.SYSTEM, "Quick test message")
        print_test_result("Debug Logger", True)
        passed += 1
    except Exception as e:
        print_test_result("Debug Logger", False, str(e))
    total += 1
    
    # Test virtual mouse
    try:
        from Logic.BackGround_Logic.Virtual_Mouse import VirtualMouse
        vm = VirtualMouse()
        print_test_result("Virtual Mouse", True, f"Type: {type(vm).__name__}")
        passed += 1
    except Exception as e:
        print_test_result("Virtual Mouse", False, str(e))
    total += 1
    
    # Test window manager
    try:
        from Logic.BackGround_Logic.Window_Manager import RobloxWindowManager
        wm = RobloxWindowManager()
        print_test_result("Window Manager", True)
        passed += 1
    except Exception as e:
        print_test_result("Window Manager", False, str(e))
    total += 1
    
    return passed, total

def run_quick_tests():
    """Run all quick tests."""
    print_test_header("QUICK TEST SUITE", "Essential functionality verification")
    
    all_passed = 0
    all_total = 0
    
    # Run tests
    test_functions = [
        quick_import_test,
        quick_file_test,
        quick_dependency_test,
        quick_project_test
    ]
    
    for test_func in test_functions:
        try:
            passed, total = test_func()
            all_passed += passed
            all_total += total
            print()
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            print(f"   {traceback.format_exc()}")
            all_total += 1
            print()
    
    # Summary
    status = summarize_test_results("Quick Tests", all_passed, all_total)
    
    # Recommendations
    print("💡 RECOMMENDATIONS")
    print("-" * 30)
    
    if status == "success":
        print("🎉 System looks good! Try running:")
        print("   python Main.py")
        print()
        print("🎮 For full testing with Roblox:")
        print("   python tests/run_all_tests.py")
    elif status == "partial":
        print("⚠️ Some issues detected, but should work:")
        print("   python Main.py")
        print()  
        print("🔍 For detailed diagnosis:")
        print("   python tests/run_all_tests.py")
    else:
        print("🚫 Major issues - check these first:")
        print("   pip install -r requirements.txt")
        print("   Verify all files in Images/ directory")
        print()
        print("🔍 For detailed diagnosis:")
        print("   python tests/test_imports.py")
    
    return status == "success" or status == "partial"

if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)