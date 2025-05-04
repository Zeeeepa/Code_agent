#!/usr/bin/env python3
"""
Test script to verify the Code Agent installation
"""

import sys
import importlib.util

def check_module(module_name):
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
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
    
    if all_passed:
        print("\nAll tests passed! Code Agent is properly installed.")
        return 0
    else:
        print("\nSome tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

