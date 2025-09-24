# Test Suite README

This document explains the testing infrastructure for the Blox Fruit Fishing project.

## Testing Infrastructure Overview

This `tests/` directory contains a comprehensive test suite to verify that the Blox Fruit Fishing automation system is working correctly.

## Quick Start

For a fast check of essential functionality:

```bash
python tests/quick_test.py
```

For comprehensive testing of all components:

```bash
python tests/run_all_tests.py
```

## Test Files

### Core Test Modules

1. **`test_imports.py`** - Dependency & Import Verification
   - Tests all Python dependencies (OpenCV, NumPy, PIL, etc.)
   - Verifies Windows API access (win32gui, ctypes)
   - Checks project module imports
   - Validates template files in Images/ directory

2. **`test_debug_logger.py`** - Debug Logger System
   - Tests centralized logging functionality
   - Verifies all log categories work
   - Tests preset switching (fishing, development, error-only)
   - Performance logging validation

3. **`test_virtual_mouse.py`** - Virtual Mouse System
   - Tests Windows API mouse control
   - Verifies cursor positioning and movement
   - Tests click simulation capabilities
   - Fallback mechanism validation

4. **`test_window_manager.py`** - Window Management
   - Tests Roblox window detection
   - Verifies window coordinate calculation
   - Tests window focus management
   - Validates window state checking

5. **`test_fishing_script.py`** - Core Automation
   - Tests main FishingBot class initialization
   - Verifies template loading and matching
   - Tests detection component imports
   - Validates OpenCV functionality

### Utility Files

1. **`test_config.py`** - Shared Test Configuration

- Common test utilities and helpers
- Project path definitions
- Standardized test output formatting
- Test result summarization

   **`quick_test.py`** - Fast Essential Tests

- Lightweight test for basic functionality
- Quick verification of core dependencies
- Minimal system health check

    **`run_all_tests.py`** - Master Test Runner

- Runs all test suites in proper order
- Provides comprehensive summary table
- Overall system assessment

## Usage Examples

### Running Individual Tests

Test specific components:

```bash
# Check all dependencies and imports
python tests/test_imports.py

# Test debug logger functionality  
python tests/test_debug_logger.py

# Test virtual mouse system
python tests/test_virtual_mouse.py

# Test window management
python tests/test_window_manager.py

# Test core fishing automation
python tests/test_fishing_script.py
```

### Running Test Suites

Quick health check:

```bash
python tests/quick_test.py
```

Full comprehensive testing:

```bash
python tests/run_all_tests.py
```

## Expected Test Results

### ✅ All Tests Pass

Your system is fully ready for fishing automation:

- All dependencies installed correctly
- All project modules import successfully  
- Templates are present and loadable
- Windows API access is working
- Virtual mouse and window management operational

### ⚠️ Partial Success  

System should work with minor limitations:

- Core functionality is available
- Some optional features may not work
- Templates or dependencies may be missing
- Proceed with caution

### ❌ Multiple Failures

System needs attention before use:

- Missing critical dependencies
- Import errors in core modules
- Template files missing
- Windows API issues

## Troubleshooting Common Issues

### Import Errors

```bash
# Install missing dependencies
pip install -r requirements.txt

# For Windows API issues
pip install pywin32
```

### Template Loading Errors

- Verify all PNG files are in `Images/` directory
- Check file permissions and corruption
- Ensure OpenCV can load image files

### Windows API Issues

- Run as Administrator if needed
- Install pywin32 package
- Check antivirus software blocking access

### Virtual Mouse Problems

- Test with administrative privileges
- Verify ctypes functionality
- Check for conflicting input software

## Test Output Interpretation

The tests use standardized symbols:

- ✅ - Test passed successfully
- ⚠️ - Warning, may work with limitations  
- ❌ - Test failed, functionality compromised
- 💡 - Informational message or tip
- 🎉 - All tests in suite passed

## Test Categories

Tests are organized by system component:

**Dependencies**: Core Python packages and Windows API
**Project Structure**: File organization and template availability
**Debug System**: Centralized logging functionality
**Input System**: Virtual mouse and keyboard control
**Window System**: Roblox window detection and management
**Automation Core**: Fish detection and minigame control

## Integration with Main System

The test suite validates the same systems used by:

- `Main.py` - GUI launcher and hotkey management
- `Logic/Fishing_Script.py` - Core automation engine
- `Logic/BackGround_Logic/` - Supporting automation modules

Tests ensure that the debug logger integration completed successfully and all components can communicate properly.

## Development Workflow

When making changes to the project:

1. Run `quick_test.py` for fast validation
2. Run specific test modules for changed components
3. Run `run_all_tests.py` before committing changes
4. Address any test failures before deployment

The tests provide confidence that the fishing automation will work correctly when deployed.
