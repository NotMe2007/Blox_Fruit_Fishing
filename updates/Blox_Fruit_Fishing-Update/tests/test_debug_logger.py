"""
Debug Logger Test Suite

Tests the centralized debug logger system functionality including:
- Basic logging functionality  
- Category filtering
- Preset switching
- Log level controls
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Logic" / "BackGround_Logic"))

def test_debug_logger_import():
    """Test that debug logger can be imported."""
    print("🧪 Testing Debug Logger Import...")
    
    try:
        from Debug_Logger import debug_log, LogCategory, DebugLogger
        print("✅ Debug logger import: OK")
        return True
    except ImportError as e:
        print(f"❌ Debug logger import failed: {e}")
        return False

def test_log_categories():
    """Test that all LogCategory values are accessible."""
    print("📂 Testing Log Categories...")
    
    try:
        from Debug_Logger import LogCategory
        
        # Test actual categories that exist
        categories = [
            LogCategory.SYSTEM,
            LogCategory.ROBLOX,
            LogCategory.CONFIG,
            LogCategory.FISH_DETECTION,
            LogCategory.ROD_DETECTION,
            LogCategory.MINIGAME_DETECT,
            LogCategory.MINIGAME,
            LogCategory.MOUSE,
            LogCategory.CASTING,
            LogCategory.WINDOW_MANAGEMENT,
            LogCategory.UI,
            LogCategory.TEMPLATE,
            LogCategory.COLOR,
            LogCategory.COORDINATES,
            LogCategory.TIMING,
            LogCategory.STATS,
            LogCategory.DEBUG,
            LogCategory.VERBOSE,
            LogCategory.ERROR
        ]
        
        print(f"✅ Found {len(categories)} log categories:")
        for cat in categories:
            print(f"   {cat.value} - {cat.name}")
        
        return True
    except Exception as e:
        print(f"❌ Log categories test failed: {e}")
        return False

def test_basic_logging():
    """Test basic logging functionality."""
    print("📝 Testing Basic Logging...")
    
    try:
        from Debug_Logger import debug_log, LogCategory
        
        print("Testing different log categories:")
        debug_log(LogCategory.DEBUG, "This is a test message")
        debug_log(LogCategory.SYSTEM, "System startup message")
        debug_log(LogCategory.ERROR, "Error handling test")
        debug_log(LogCategory.FISH_DETECTION, "Fish detection test")
        
        print("✅ Basic logging: OK")
        return True
    except Exception as e:
        print(f"❌ Basic logging test failed: {e}")
        return False

def test_preset_system():
    """Test the preset switching system."""
    print("🎛️ Testing Preset System...")
    
    try:
        from Debug_Logger import set_preset, get_logger_status
        from Debug_Config import DEFAULT_PRESET
        
        print(f"Current default preset: {DEFAULT_PRESET}")
        
        # Test preset switching
        print("\nTesting preset switches:")
        
        set_preset('ALL_ENABLED')
        print("✅ Set to ALL_ENABLED preset")
        
        set_preset('MINIMAL') 
        print("✅ Set to MINIMAL preset")
        
        set_preset('FISH_DEBUG')
        print("✅ Set to FISH_DEBUG preset")
        
        set_preset('MINIGAME_DEBUG')
        print("✅ Set to MINIGAME_DEBUG preset")
        
        # Reset to default
        set_preset(DEFAULT_PRESET)
        print(f"✅ Reset to {DEFAULT_PRESET} preset")
        
        return True
    except Exception as e:
        print(f"❌ Preset system test failed: {e}")
        return False

def test_logger_status():
    """Test logger status reporting."""
    print("📊 Testing Logger Status...")
    
    try:
        from Debug_Logger import get_logger_status
        
        status = get_logger_status()
        print("Current logger status:")
        print(status)
        
        print("✅ Logger status: OK")
        return True
    except Exception as e:
        print(f"❌ Logger status test failed: {e}")
        return False

def test_performance_logging():
    """Test performance logging features."""
    print("⚡ Testing Performance Logging...")
    
    try:
        from Debug_Logger import debug_log, LogCategory
        import time
        
        # Test timestamp logging
        debug_log(LogCategory.TIMING, "Performance test starting...")
        
        # Simulate some work
        time.sleep(0.1)
        
        debug_log(LogCategory.TIMING, "Performance test completed")
        
        print("✅ Performance logging: OK")
        return True
    except Exception as e:
        print(f"❌ Performance logging test failed: {e}")
        return False

def run_debug_logger_tests():
    """Run all debug logger tests."""
    print("=" * 60)
    print("🧪 DEBUG LOGGER TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        test_debug_logger_import,
        test_log_categories,
        test_basic_logging,
        test_preset_system,
        test_logger_status,
        test_performance_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            print()
    
    # Summary
    print("=" * 60)
    print("📊 DEBUG LOGGER TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL DEBUG LOGGER TESTS PASSED!")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed!")
        return False

if __name__ == "__main__":
    success = run_debug_logger_tests()
    sys.exit(0 if success else 1)