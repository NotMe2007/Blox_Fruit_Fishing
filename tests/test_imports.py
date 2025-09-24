"""
Test Import Verification for Blox Fruit Fishing Project

This module tests that all critical imports work correctly and modules are available.
Run this test to verify your environment is set up properly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Logic"))
sys.path.insert(0, str(project_root / "Logic" / "BackGround_Logic"))

def test_core_imports():
    """Test that all core Python libraries are available."""
    print("🧪 Testing Core Python Imports...")
    
    try:
        import time
        import sys  
        import os
        import cv2
        import numpy as np
        import random
        import math
        from pathlib import Path
        from enum import Enum
        print("✅ Core imports: OK")
        return True
    except ImportError as e:
        print(f"❌ Core imports failed: {e}")
        return False

def test_windows_api_imports():
    """Test Windows API imports for mouse and window management."""
    print("🪟 Testing Windows API Imports...")
    
    try:
        import win32gui
        import win32con
        import ctypes
        import ctypes.wintypes
        print("✅ Windows API imports: OK")
        return True
    except ImportError as e:
        print(f"❌ Windows API imports failed: {e}")
        print("💡 Install pywin32: pip install pywin32")
        return False

def test_optional_imports():
    """Test optional imports that have fallbacks."""
    print("🔧 Testing Optional Imports...")
    
    results = {}
    
    # Test keyboard
    try:
        import keyboard
        results['keyboard'] = True
        print("✅ keyboard: Available")
    except ImportError:
        results['keyboard'] = False
        print("⚠️ keyboard: Not available (hotkeys won't work)")
    
    # Test customtkinter
    try:
        import customtkinter
        results['customtkinter'] = True
        print("✅ customtkinter: Available")
    except ImportError:
        results['customtkinter'] = False
        print("⚠️ customtkinter: Not available (will use tkinter fallback)")
    
    # Test mss (for screenshots)
    try:
        import mss
        results['mss'] = True
        print("✅ mss: Available")
    except ImportError:
        results['mss'] = False
        print("⚠️ mss: Not available (will use fallback screenshot methods)")
    
    return results

def test_project_imports():
    """Test that our project modules can be imported."""
    print("📁 Testing Project Module Imports...")
    
    results = {}
    
    # Test Debug Logger
    try:
        from Logic.BackGround_Logic.Debug_Logger import debug_log, LogCategory
        results['Debug_Logger'] = True
        print("✅ Debug_Logger: OK")
    except ImportError as e:
        results['Debug_Logger'] = False
        print(f"❌ Debug_Logger failed: {e}")
    
    # Test Virtual Mouse
    try:
        from Logic.BackGround_Logic.Virtual_Mouse import VirtualMouse
        results['Virtual_Mouse'] = True
        print("✅ Virtual_Mouse: OK")
    except ImportError as e:
        results['Virtual_Mouse'] = False
        print(f"❌ Virtual_Mouse failed: {e}")
    
    # Test Window Manager
    try:
        from Logic.BackGround_Logic.Window_Manager import RobloxWindowManager
        results['Window_Manager'] = True
        print("✅ Window_Manager: OK")
    except ImportError as e:
        results['Window_Manager'] = False
        print(f"❌ Window_Manager failed: {e}")
    
    # Test Fishing Rod Detector
    try:
        from Logic.BackGround_Logic.Fishing_Rod_Detector import FishingRodDetector
        results['Fishing_Rod_Detector'] = True
        print("✅ Fishing_Rod_Detector: OK")
    except ImportError as e:
        results['Fishing_Rod_Detector'] = False
        print(f"❌ Fishing_Rod_Detector failed: {e}")
    
    # Test Fishing Mini Game
    try:
        from Logic.BackGround_Logic.Fishing_Mini_Game import MinigameController
        results['Fishing_Mini_Game'] = True
        print("✅ Fishing_Mini_Game: OK")
    except ImportError as e:
        results['Fishing_Mini_Game'] = False
        print(f"❌ Fishing_Mini_Game failed: {e}")
    
    # Test Main Fishing Script
    try:
        from Logic import Fishing_Script
        results['Fishing_Script'] = True
        print("✅ Fishing_Script: OK")
    except ImportError as e:
        results['Fishing_Script'] = False
        print(f"❌ Fishing_Script failed: {e}")
    
    return results

def test_template_files():
    """Test that template image files exist."""
    print("🖼️ Testing Template Files...")
    
    images_dir = project_root / "Images"
    required_templates = [
        "Fish_On_Hook.png",
        "Fish_Left.png", 
        "Fish_Right.png",
        "MiniGame_Bar.png",
        "Basic_Fishing_EQ.png",
        "Basic_Fishing_UN.png"
    ]
    
    results = {}
    for template in required_templates:
        template_path = images_dir / template
        if template_path.exists():
            results[template] = True
            print(f"✅ {template}: Found")
        else:
            results[template] = False
            print(f"❌ {template}: Missing")
    
    return results

def run_all_tests():
    """Run all import and availability tests."""
    print("=" * 60)
    print("🚀 BLOX FRUIT FISHING - IMPORT TEST SUITE")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Core imports (critical)
    if not test_core_imports():
        all_passed = False
    print()
    
    # Windows API (critical)  
    if not test_windows_api_imports():
        all_passed = False
    print()
    
    # Optional imports (warnings only)
    optional_results = test_optional_imports()
    print()
    
    # Project modules (critical)
    project_results = test_project_imports()
    if not all(project_results.values()):
        all_passed = False
    print()
    
    # Template files (warnings only)
    template_results = test_template_files()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if all_passed:
        print("🎉 ALL CRITICAL TESTS PASSED!")
        print("✅ Your environment is ready for fishing automation.")
    else:
        print("⚠️ SOME CRITICAL TESTS FAILED!")
        print("❌ Please fix the issues above before running the fishing bot.")
    
    # Optional summary
    optional_available = sum(1 for v in optional_results.values() if v)
    optional_total = len(optional_results)
    print(f"📦 Optional packages: {optional_available}/{optional_total} available")
    
    # Template summary
    templates_found = sum(1 for v in template_results.values() if v)
    templates_total = len(template_results)
    print(f"🖼️ Template files: {templates_found}/{templates_total} found")
    
    print()
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)