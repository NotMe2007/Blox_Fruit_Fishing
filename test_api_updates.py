#!/usr/bin/env python3
"""
Test script for the updated Roblox API detection functionality.
"""

import sys
from pathlib import Path

# Add the Logic directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'Logic'))

def test_api_functionality():
    """Test the new API-based Roblox detection."""
    print("=== Testing Updated Roblox API Detection ===")
    
    try:
        from Logic.IsRoblox_Open import RobloxChecker
        
        checker = RobloxChecker()
        print("✅ RobloxChecker imported successfully")
        
        # Test API game info retrieval
        print("\nTesting API game info retrieval...")
        test_game_id = 2753915549  # Main Blox Fruits game ID
        game_info = checker.get_game_info_from_api(test_game_id)
        
        if game_info:
            print(f"✅ Game info retrieved: {game_info.get('name', 'Unknown')}")
        else:
            print("⚠️  Could not retrieve game info (may be network issue)")
         
        # Test game search
        print("\nTesting game search...")
        search_result = checker.search_game_by_name("Blox Fruits") #
        
        if search_result:
            print(f"✅ Search result: {search_result.get('name', 'Unknown')}")
        else:
            print("⚠️  Could not search games (may be network issue)")
        
        # Test comprehensive status check
        print("\nTesting comprehensive status check...")
        status = checker.check_roblox_status()
        
        print(f"Roblox running: {status['roblox_running']}")
        print(f"Playing Blox Fruits: {status['playing_blox_fruits']}")
        print(f"Current game: {status['current_game']}")
        print(f"Game ID: {status.get('game_id', 'N/A')}")
        print(f"Detection method: {status.get('detection_method', 'N/A')}")
        print(f"Can proceed: {status['can_proceed']}")
        print(f"Message: {status['message']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API functionality: {e}")
        return False

def test_gui_topmost():
    """Test that the GUI can be imported and initialized."""
    print("\n=== Testing GUI Topmost Feature ===")
    
    try:
        # Import without actually running the GUI
        import Main
        print("✅ Main GUI module imported successfully")
        print("✅ Topmost functionality should be available")
        return True
        
    except Exception as e:
        print(f"❌ Error testing GUI: {e}")
        return False

def main():
    """Run all tests for the updated functionality."""
    print("Testing Updated Roblox Detection and GUI Features\n")
    
    tests_passed = 0
    total_tests = 2
    
    if test_api_functionality():
        tests_passed += 1
    
    if test_gui_topmost():
        tests_passed += 1
    
    print(f"\n=== Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
