"""
Master Test Runner

Runs all test suites in the proper order and provides comprehensive results.
This is the main entry point for testing the entire Blox Fruit Fishing project.
"""

import sys
import os
from pathlib import Path
import importlib.util
import subprocess
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_module(test_file_path):
    """Run a test module and capture results."""
    print(f"🏃 Running {test_file_path.name}...")
    print("=" * 50)
    
    try:
        # Load and run the test module
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load test module spec for {test_file_path}")
        test_module = importlib.util.module_from_spec(spec)
        
        # Capture stdout to determine test results
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        start_time = time.time()
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                spec.loader.exec_module(test_module)
                
                # Call the main test function if it exists
                main_func_name = f"run_{test_file_path.stem.replace('test_', '')}_tests"
                if hasattr(test_module, main_func_name):
                    result = getattr(test_module, main_func_name)()
                else:
                    result = True  # Assume success if no main function
                    
        except SystemExit as e:
            result = e.code == 0
        except Exception as e:
            result = False
            stderr_buffer.write(f"Exception: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get outputs
        stdout_content = stdout_buffer.getvalue()
        stderr_content = stderr_buffer.getvalue()
        
        # Print the actual output
        print(stdout_content)
        if stderr_content:
            print("STDERR:", stderr_content)
        
        print(f"⏱️ Test completed in {duration:.2f}s")
        print("=" * 50)
        print()
        
        return result, stdout_content, stderr_content, duration
        
    except Exception as e:
        print(f"❌ Failed to run {test_file_path.name}: {e}")
        print("=" * 50)
        print()
        return False, "", str(e), 0

def analyze_test_output(test_name, stdout_content):
    """Analyze test output to extract useful information."""
    lines = stdout_content.split('\n')
    
    # Count test indicators
    passed_indicators = ['✅', 'OK', 'PASSED']
    warning_indicators = ['⚠️', 'WARNING', 'Not available']
    failed_indicators = ['❌', 'FAILED', 'ERROR']
    
    passed_count = sum(1 for line in lines for indicator in passed_indicators if indicator in line)
    warning_count = sum(1 for line in lines for indicator in warning_indicators if indicator in line)
    failed_count = sum(1 for line in lines for indicator in failed_indicators if indicator in line)
    
    return {
        'name': test_name,
        'passed': passed_count,
        'warnings': warning_count,
        'failures': failed_count,
        'total_indicators': passed_count + warning_count + failed_count
    }

def print_summary_table(test_results):
    """Print a nice summary table of all test results."""
    print("📊 TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"{'Test Suite':<25} {'Status':<10} {'✅ Pass':<8} {'⚠️ Warn':<8} {'❌ Fail':<8} {'Duration':<10}")
    print("-" * 80)
    
    total_passed = 0
    total_warnings = 0
    total_failures = 0
    total_duration = 0
    
    for result in test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        if result['analysis']['warnings'] > result['analysis']['failures'] and result['success']:
            status = "⚠️ WARN"
        
        print(f"{result['name']:<25} {status:<10} "
              f"{result['analysis']['passed']:<8} "
              f"{result['analysis']['warnings']:<8} "
              f"{result['analysis']['failures']:<8} "
              f"{result['duration']:.2f}s")
        
        total_passed += result['analysis']['passed']
        total_warnings += result['analysis']['warnings'] 
        total_failures += result['analysis']['failures']
        total_duration += result['duration']
    
    print("-" * 80)
    print(f"{'TOTALS':<25} {'':<10} {total_passed:<8} {total_warnings:<8} {total_failures:<8} {total_duration:.2f}s")
    print("=" * 80)
    print()

def main():
    """Run all tests and provide comprehensive summary."""
    print("🧪 BLOX FRUIT FISHING - MASTER TEST SUITE")
    print("=" * 60)
    print("Testing all components of the fishing automation system")
    print("=" * 60)
    print()
    
    # Find all test files
    tests_dir = Path(__file__).parent
    test_files = [
        tests_dir / "test_imports.py",
        tests_dir / "test_debug_logger.py", 
        tests_dir / "test_virtual_mouse.py",
        tests_dir / "test_fishing_rod_detector.py",
        tests_dir / "test_window_manager.py",
        tests_dir / "test_fishing_script.py"
    ]
    
    # Filter to existing files
    existing_tests = [f for f in test_files if f.exists()]
    missing_tests = [f for f in test_files if not f.exists()]
    
    if missing_tests:
        print("⚠️ Missing test files:")
        for missing in missing_tests:
            print(f"   ❌ {missing.name}")
        print()
    
    print(f"🏃 Running {len(existing_tests)} test suites...")
    print()
    
    # Run all tests
    test_results = []
    overall_success = True
    
    for test_file in existing_tests:
        success, stdout, stderr, duration = run_test_module(test_file)
        analysis = analyze_test_output(test_file.stem, stdout)
        
        test_results.append({
            'name': test_file.stem,
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'duration': duration,
            'analysis': analysis
        })
        
        if not success:
            overall_success = False
    
    # Print comprehensive summary
    print_summary_table(test_results)
    
    # Overall assessment
    successful_tests = sum(1 for r in test_results if r['success'])
    total_tests = len(test_results)
    
    print("🎯 OVERALL ASSESSMENT")
    print("=" * 40)
    print(f"Test suites passed: {successful_tests}/{total_tests}")
    
    if overall_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Blox Fruit Fishing automation is ready to use!")
        print()
        print("Next steps:")
        print("1. Start Roblox and join Blox Fruits")
        print("2. Run Main.py to start the fishing automation")
        print("3. Use numpad hotkeys to control the bot")
    elif successful_tests >= total_tests - 1:
        print("✅ MOSTLY WORKING!")
        print("⚠️ Minor issues detected, but system should function")
        print()
        print("Recommendations:")
        print("1. Check missing dependencies in failed tests")
        print("2. System should still work with some limitations")
        print("3. Start Roblox for full functionality testing")
    else:
        print("❌ MULTIPLE TEST FAILURES!")
        print("🚫 System may not work properly")
        print()
        print("Recommended actions:")
        print("1. Check Python environment and install missing packages")
        print("2. Verify all template files are in Images/ directory")
        print("3. Ensure Windows API access is available")
        print("4. Run individual test suites to identify specific issues")
    
    print()
    print("💡 For detailed logs, check individual test outputs above")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)