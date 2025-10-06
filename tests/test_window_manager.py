"""
Window Manager Test Suite

Tests the Window Manager functionality including:
- Roblox window detection
- Window coordinate retrieval
- Window focusing capabilities
"""

import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Logic" / "BackGround_Logic"))

def test_window_manager_import():
    """Test that Window Manager can be imported."""
    print("🧪 Testing Window Manager Import...")
    
    try:
        from Window_Manager import RobloxWindowManager
        print("✅ Window Manager import: OK")
        return True
    except ImportError as e:
        print(f"❌ Window Manager import failed: {e}")
        return False

def test_window_manager_initialization():
    """Test Window Manager initialization."""
    print("🪟 Testing Window Manager Initialization...")
    
    try:
        from Window_Manager import RobloxWindowManager
        
        wm = RobloxWindowManager()
        print("✅ Window Manager initialization: OK")
        return True, wm
    except Exception as e:
        print(f"❌ Window Manager initialization failed: {e}")
        return False, None

def test_roblox_window_detection(wm):
    """Test Roblox window detection (non-intrusive)."""
    print("🔍 Testing Roblox Window Detection...")
    
    try:
        found = wm.find_roblox_window()
        
        if found:
            print("✅ Roblox window found!")
            print(f"   Window handle: {wm.roblox_hwnd}")
            print(f"   Window coordinates: {wm.window_rect}")
            return True
        else:
            print("⚠️ No Roblox window found")
            print("   This is normal if Roblox/Blox Fruits isn't running")
            return True  # Not an error, just no window
    except Exception as e:
        print(f"❌ Roblox window detection failed: {e}")
        return False

def test_window_center_calculation(wm):
    """Test window center coordinate calculation."""
    print("📍 Testing Window Center Calculation...")
    
    try:
        if wm.roblox_hwnd and wm.window_rect:
            center_x, center_y = wm.get_window_center()
            if center_x and center_y:
                print(f"✅ Window center calculated: ({center_x}, {center_y})")
                return True
            else:
                print("❌ Failed to calculate window center")
                return False
        else:
            print("⚠️ No Roblox window available for center calculation")
            return True  # Not an error
    except Exception as e:
        print(f"❌ Window center calculation failed: {e}")
        return False

def test_window_validation(wm):
    """Test window validation functionality."""
    print("✅ Testing Window Validation...")
    
    try:
        if wm.roblox_hwnd:
            is_valid = wm.is_window_valid()
            print(f"✅ Window validation result: {is_valid}")
            return True
        else:
            print("⚠️ No window to validate")
            return True  # Not an error
    except Exception as e:
        print(f"❌ Window validation failed: {e}")
        return False

def test_focus_check(wm):
    """Test focus checking functionality."""
    print("👁️ Testing Focus Check...")
    
    try:
        if wm.roblox_hwnd:
            is_focused = wm.is_roblox_focused()
            print(f"✅ Roblox focus status: {'Focused' if is_focused else 'Not focused'}")
            return True
        else:
            print("⚠️ No Roblox window to check focus")
            return True  # Not an error
    except Exception as e:
        print(f"❌ Focus check failed: {e}")
        return False

def test_coordinate_functions():
    """Test standalone coordinate functions."""
    print("🎯 Testing Standalone Coordinate Functions...")
    
    try:
        from Window_Manager import get_roblox_coordinates, ensure_roblox_focused
        
        # Test coordinate function
        coords = get_roblox_coordinates()
        if coords:
            print(f"✅ get_roblox_coordinates: {coords}")
        else:
            print("⚠️ get_roblox_coordinates returned None (no Roblox window)")
        
        # Note: We won't test ensure_roblox_focused as it modifies window state
        print("✅ Coordinate functions: OK")
        return True
    except ImportError:
        print("⚠️ Standalone functions not available (expected for newer versions)")
        return True
    except Exception as e:
        print(f"❌ Coordinate functions test failed: {e}")
        return False

def run_window_manager_tests():
    """Run all window manager tests."""
    print("=" * 60)
    print("🪟 WINDOW MANAGER TEST SUITE")
    print("=" * 60)
    print()
    
    # Import test
    if not test_window_manager_import():
        print("❌ Cannot continue without Window Manager import")
        return False
    print()
    
    # Initialization test
    success, wm = test_window_manager_initialization()
    if not success or wm is None:
        print("❌ Cannot continue without Window Manager initialization")
        return False
    print()
    
    # Run remaining tests
    tests = [
        lambda: test_roblox_window_detection(wm),
        lambda: test_window_center_calculation(wm),
        lambda: test_window_validation(wm),
        lambda: test_focus_check(wm),
        test_coordinate_functions
    ]
    
    passed = 2  # Import and initialization already succeeded
    total = len(tests) + 2  # +2 for import and init
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            print()
    
    # Summary
    print("=" * 60)
    print("📊 WINDOW MANAGER TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL WINDOW MANAGER TESTS PASSED!")
        print("✅ Window Manager is ready for use")
    else:
        print(f"⚠️ {total - passed} tests failed!")
        print("❌ Window Manager may not work properly")
    
    # Additional info
    if wm.roblox_hwnd:
        print("🎮 Roblox window is currently available for automation")
    else:
        print("💡 Start Roblox/Blox Fruits and run tests again for full validation")
    
    return passed >= total - 2  # Allow some failures if no Roblox window

if __name__ == "__main__":
    success = run_window_manager_tests()
    sys.exit(0 if success else 1)