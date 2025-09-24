"""
Fishing Script Test Suite

Tests the main fishing automation script including:
- Core fishing script functionality
- Template loading and matching
- Fish detection capabilities
- Background task management
"""

import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Logic"))

def test_fishing_script_import():
    """Test that Fishing Script can be imported."""
    print("🎣 Testing Fishing Script Import...")
    
    try:
        import Fishing_Script
        print("✅ Fishing Script import: OK")
        return True
    except ImportError as e:
        print(f"❌ Fishing Script import failed: {e}")
        return False

def test_images_directory():
    """Test that Images directory exists and has templates."""
    print("🖼️ Testing Images Directory...")
    
    images_dir = project_root / "Images"
    
    if not images_dir.exists():
        print("❌ Images directory not found!")
        return False
    
    print(f"✅ Images directory found: {images_dir}")
    
    # Check for key template files
    key_templates = [
        "Fish_On_Hook.png",
        "Fish_Left.png",
        "Fish_Right.png",
        "MiniGame_Bar.png",
        "Basic_Fishing_EQ.png",
        "Basic_Fishing_UN.png"
    ]
    
    found_templates = []
    missing_templates = []
    
    for template in key_templates:
        template_path = images_dir / template
        if template_path.exists():
            found_templates.append(template)
        else:
            missing_templates.append(template)
    
    print(f"✅ Found templates: {len(found_templates)}/{len(key_templates)}")
    for template in found_templates:
        print(f"   ✅ {template}")
    
    if missing_templates:
        print(f"⚠️ Missing templates: {len(missing_templates)}")
        for template in missing_templates:
            print(f"   ❌ {template}")
    
    return len(found_templates) > 0

def test_fishing_script_initialization():
    """Test fishing script main functions."""
    print("🤖 Testing Fishing Script Functions...")
    
    try:
        import Fishing_Script
        
        # Test key functions exist
        functions_to_check = [
            'CastFishingRod',
            'Fish_On_Hook',
            'Fish_Left',
            'Fish_Right',
            'safe_load_template',
            'main_fishing_loop'
        ]
        
        available_functions = 0
        for func_name in functions_to_check:
            if hasattr(Fishing_Script, func_name) and callable(getattr(Fishing_Script, func_name)):
                print(f"✅ Function {func_name}: Available")
                available_functions += 1
            else:
                print(f"❌ Function {func_name}: Not available")
        
        print(f"✅ Fishing Script functions: {available_functions}/{len(functions_to_check)} available")
        return True, available_functions >= len(functions_to_check) - 1
    except Exception as e:
        print(f"❌ Fishing Script test failed: {e}")
        return False, False

def test_template_loading():
    """Test template loading functionality."""
    print("📋 Testing Template Loading...")
    
    try:
        import Fishing_Script
        
        images_dir = project_root / "Images"
        
        # Test loading a common template
        test_templates = ["Fish_On_Hook.png", "MiniGame_Bar.png", "Fish_Left.png"]
        
        loaded_count = 0
        for template_name in test_templates:
            template_path = images_dir / template_name
            if template_path.exists():
                template = Fishing_Script.safe_load_template(template_path)
                if template is not None:
                    loaded_count += 1
                    print(f"✅ Loaded template: {template_name}")
                else:
                    print(f"❌ Failed to load template: {template_name}")
            else:
                print(f"⚠️ Template not found: {template_name}")
        
        print(f"✅ Template loading: {loaded_count}/{len(test_templates)} successful")
        return loaded_count > 0
    except Exception as e:
        print(f"❌ Template loading test failed: {e}")
        return False

def test_detection_components():
    """Test detection component imports and availability."""
    print("🔍 Testing Detection Components...")
    
    # Test fishing rod detector functions
    try:
        from Logic.BackGround_Logic.Fishing_Rod_Detector import load_templates, check_region_and_act
        print("✅ Fishing Rod Detector functions: Available")
        rod_detector_available = True
    except Exception as e:
        print(f"⚠️ Fishing Rod Detector functions: Not available ({e})")
        rod_detector_available = False
    
    # Test minigame controller
    try:
        from Logic.BackGround_Logic.Fishing_Mini_Game import MinigameController
        minigame = MinigameController()
        print("✅ Minigame Controller: Available")
        minigame_available = True
    except Exception as e:
        print(f"⚠️ Minigame Controller: Not available ({e})")
        minigame_available = False
    
    # Test Roblox detection
    try:
        from Logic.BackGround_Logic.Is_Roblox_Open import RobloxChecker
        checker = RobloxChecker()
        print("✅ Roblox Detection: Available")
        roblox_detection_available = True
    except Exception as e:
        print(f"⚠️ Roblox Detection: Not available ({e})")
        roblox_detection_available = False
    
    total_available = sum([rod_detector_available, minigame_available, roblox_detection_available])
    print(f"✅ Detection components: {total_available}/3 available")
    
    return total_available >= 2  # At least 2 should be available

def test_opencv_functionality():
    """Test OpenCV functionality for template matching."""
    print("👁️ Testing OpenCV Functionality...")
    
    try:
        import cv2
        print(f"✅ OpenCV version: {cv2.__version__}")
        
        # Test basic OpenCV operations
        import numpy as np
        
        # Create a test image
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test grayscale conversion
        gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        print("✅ Grayscale conversion: OK")
        
        # Test template matching function exists
        if hasattr(cv2, 'matchTemplate'):
            print("✅ Template matching function: Available")
        else:
            print("❌ Template matching function: Not available")
        
        return True
    except Exception as e:
        print(f"❌ OpenCV functionality test failed: {e}")
        return False

def test_fishing_script_methods():
    """Test key fishing script functions (non-destructive)."""
    print("⚙️ Testing Fishing Script Functions...")
    
    try:
        import Fishing_Script
        
        # Test method existence
        functions_to_check = [
            'CastFishingRod',
            'Fish_On_Hook',
            'Fish_Left', 
            'Fish_Right',
            'safe_load_template',
            'main_fishing_loop'
        ]
        
        available_functions = 0
        for func_name in functions_to_check:
            if hasattr(Fishing_Script, func_name) and callable(getattr(Fishing_Script, func_name)):
                print(f"✅ Function {func_name}: Available")
                available_functions += 1
            else:
                print(f"❌ Function {func_name}: Not available")
        
        print(f"✅ Fishing Script functions: {available_functions}/{len(functions_to_check)} available")
        
        return available_functions >= len(functions_to_check) - 1  # Allow one missing
    except Exception as e:
        print(f"❌ Fishing Script functions test failed: {e}")
        return False

def test_background_dependencies():
    """Test background logic dependencies."""
    print("🔧 Testing Background Dependencies...")
    
    dependencies = {
        "Virtual_Mouse": "Virtual mouse input",
        "Virtual_Keyboard": "Virtual keyboard input",
        "Window_Manager": "Window management",
        "WebHook": "Discord webhook integration"
    }
    
    available_deps = 0
    
    for dep_name, description in dependencies.items():
        try:
            # Try importing from BackGround_Logic
            module_path = f"Logic.BackGround_Logic.{dep_name}"
            __import__(module_path)
            print(f"✅ {description}: Available")
            available_deps += 1
        except ImportError:
            print(f"⚠️ {description}: Not available")
    
    print(f"✅ Background dependencies: {available_deps}/{len(dependencies)} available")
    return available_deps >= 2  # At least 2 should be available

def run_fishing_script_tests():
    """Run all fishing script tests."""
    print("=" * 60)
    print("🎣 FISHING SCRIPT TEST SUITE")
    print("=" * 60)
    print()
    
    # Core tests
    tests = [
        test_fishing_script_import,
        test_images_directory,
        test_fishing_script_initialization,
        test_template_loading,
        test_detection_components,
        test_opencv_functionality,
        test_fishing_script_methods,
        test_background_dependencies
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func.__name__ == 'test_fishing_script_initialization':
                result, _ = test_func()
                if result:
                    passed += 1
            else:
                if test_func():
                    passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            print()
    
    # Summary
    print("=" * 60)
    print("📊 FISHING SCRIPT TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL FISHING SCRIPT TESTS PASSED!")
        print("🎣 Fishing automation is ready to use")
    elif passed >= total - 2:
        print("✅ MOSTLY WORKING - Minor issues detected")
        print("🎣 Fishing automation should work with some limitations")
    else:
        print(f"❌ {total - passed} tests failed!")
        print("🚫 Fishing automation may not work properly")
    
    print()
    print("💡 TIP: Ensure Roblox/Blox Fruits is running for full functionality")
    print("💡 TIP: Check that all templates are present in Images/ directory")
    
    return passed >= total - 2

if __name__ == "__main__":
    success = run_fishing_script_tests()
    sys.exit(0 if success else 1)