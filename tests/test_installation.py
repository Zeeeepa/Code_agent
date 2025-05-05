#!/usr/bin/env python3
"""
Test script to verify the Code Agent installation
"""

import sys
import importlib.util
import subprocess
import platform

def check_module(module_name):
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def check_command(command):
    """Check if a command can be executed."""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.returncode == 0
    except Exception:
        return False

def main():
    """Main test function."""
    print("Testing Code Agent installation...")
    
    # Check core modules
    core_modules = [
        "code_agent",
        "code_agent.core.config",
        "code_agent.core.context_manager",
        "code_agent.core.integration",
        "code_agent.core.issue_solver",
        "code_agent.core.workflow",
        "code_agent.runner",
        "code_agent.demo"
    ]
    
    all_passed = True
    for module in core_modules:
        if check_module(module):
            print(f"✅ {module} - OK")
        else:
            print(f"❌ {module} - FAILED")
            all_passed = False
    
    # Check dependencies
    dependencies = [
        "github",
        "pyngrok",
        "requests"
    ]
    
    print("\nChecking dependencies...")
    for dep in dependencies:
        if check_module(dep):
            print(f"✅ {dep} - OK")
        else:
            print(f"❌ {dep} - FAILED")
            all_passed = False
    
    # Check CLI command
    print("\nChecking CLI command...")
    cli_command = "code-agent --help"
    if check_command(cli_command):
        print(f"✅ CLI command - OK")
    else:
        print(f"❌ CLI command - FAILED")
        print("  Note: You may need to restart your terminal or add the installation directory to your PATH.")
        all_passed = False
    
    # Check module command
    print("\nChecking module command...")
    module_command = "python -m code_agent --help"
    if check_command(module_command):
        print(f"✅ Module command - OK")
    else:
        print(f"❌ Module command - FAILED")
        all_passed = False
    
    if all_passed:
        print("\nAll tests passed! Code Agent is properly installed.")
        return 0
    else:
        print("\nSome tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

