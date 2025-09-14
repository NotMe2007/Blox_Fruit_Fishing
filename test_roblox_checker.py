#!/usr/bin/env python3
"""
Test script to demonstrate the Roblox checker functionality.
This script will continuously check for Roblox and Blox Fruits status. 
"""

import time
from Logic.IsRoblox_Open import RobloxChecker

def main():
    """Main test function."""
    print("=== Roblox and Blox Fruits Checker Test ===")
    print("This script will check every 5 seconds for Roblox and Blox Fruits status.")
    print("Press Ctrl+C to exit.\n")
    
    checker = RobloxChecker() #
    
    try:
        while True:
            print("Checking Roblox status...")
            status = checker.check_roblox_status()
            
            print(f"🎮 Roblox running: {'✅ Yes' if status['roblox_running'] else '❌ No'}")
            print(f"🏴‍☠️ Playing Blox Fruits: {'✅ Yes' if status['playing_blox_fruits'] else '❌ No'}")
            
            if status['current_game']:
                print(f"🎯 Current game: {status['current_game']}")
            
            print(f"🚀 Can proceed: {'✅ Yes' if status['can_proceed'] else '❌ No'}")
            print(f"💬 Message: {status['message']}")
            print("-" * 50)
            #
            if status['can_proceed']:
                print("🎉 Ready to start fishing! Exiting test...")
                break
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n👋 Test stopped by user.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
