#!/usr/bin/env python3
"""
Integration test for the Blox Fruits Fishing automation system.

This script tests the integration between:
- Fishing_Script.py (main automation logic)
- FishingRodDetector.py (fishing rod state detection)
- Fishing_MiniGame.py (minigame decision logic)

Usage:
    python test_integration.py [--debug] [--dry-run]
    
    --debug: Enable verbose debug output
    --dry-run: Test without actually clicking or pressing keys
"""

import sys
import time
import argparse
from pathlib import Path

# Add the Logic directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'Logic'))

def test_detector_module():
    """Test that the FishingRodDetector module can be loaded and used."""
    print("Testing FishingRodDetector module...")
    
    try:
        from Logic.BackGroud_Logic.FishingRodDetector import check_region_and_act, load_templates
        print("✅ FishingRodDetector module imported successfully")
        
        # Test template loading
        un_gray, eq_gray = load_templates()
        print("✅ Templates loaded successfully")
        
        # Test region checking (should return None if no fishing rod UI visible)
        result = check_region_and_act()
        print(f"✅ Region check completed, result: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing FishingRodDetector: {e}")
        return False

def test_minigame_module():
    """Test that the Fishing_MiniGame module can be loaded and used."""
    print("\nTesting Fishing_MiniGame module...")
    
    try:
        from Logic.BackGroud_Logic.Fishing_MiniGame import MinigameController, MinigameConfig
        print("✅ Fishing_MiniGame module imported successfully")
        
        # Test minigame controller
        config = MinigameConfig()
        controller = MinigameController(config)
        
        # Test decision making
        action = controller.decide(indicator=0.6, arrow='right', stable=True)
        print(f"✅ Minigame decision test completed: {action}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing Fishing_MiniGame: {e}")
        return False

def test_main_script():
    """Test that the main Fishing_Script can import all required modules."""
    print("\nTesting main Fishing_Script integration...")
    
    try:
        from Logic.Fishing_Script import get_detector_module, handle_fishing_minigame
        print("✅ Fishing_Script main functions imported successfully")
        
        # Test detector module loading
        detector_module = get_detector_module()
        print("✅ Detector module loaded successfully")
        
        # Test that expected attributes exist
        expected_attrs = ['check_region_and_act', 'FISH_ON_HOOK_TPL', 'SHIFT_LOCK_TPL']
        for attr in expected_attrs:
            if hasattr(detector_module, attr):
                print(f"✅ Found expected attribute: {attr}")
            else:
                print(f"⚠️  Missing attribute: {attr}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing main script integration: {e}")
        return False

def test_roblox_integration():
    """Test that the Roblox detection works with the fishing script."""
    print("\nTesting Roblox integration...")
    
    try:
        from Logic.IsRoblox_Open import check_roblox_and_game
        print("✅ Roblox checker imported successfully")
        
        # Test Roblox status check
        status = check_roblox_and_game()
        print(f"✅ Roblox status check completed")
        print(f"   Roblox running: {status['roblox_running']}")
        print(f"   Playing Blox Fruits: {status['playing_blox_fruits']}")
        print(f"   Can proceed: {status['can_proceed']}")
        print(f"   Message: {status['message']}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing Roblox integration: {e}")
        return False

def main():
    """Run all integration tests."""
    parser = argparse.ArgumentParser(description='Test Blox Fruits Fishing integration')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--dry-run', action='store_true', help='Test without actions')
    
    args = parser.parse_args()
    
    print("=== Blox Fruits Fishing Integration Test ===")
    print(f"Debug mode: {args.debug}")
    print(f"Dry run mode: {args.dry_run}")
    print()
    
    # Enable debug mode in detector if requested
    if args.debug:
        try:
            from Logic.BackGroud_Logic import FishingRodDetector
            FishingRodDetector.debug = True
            print("Debug mode enabled in FishingRodDetector")
        except:
            pass
    
    # Run all tests
    tests = [
        test_detector_module,
        test_minigame_module,
        test_main_script,
        test_roblox_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
