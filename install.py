#!/usr/bin/env python3
"""
Installation script for Code Agent
"""

import os
import sys
import subprocess
import argparse

def run_command(command):
    """Run a shell command and return the output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Install Code Agent")
    parser.add_argument("--dev", action="store_true", help="Install in development mode")
    parser.add_argument("--test", action="store_true", help="Run tests after installation")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Code Agent Installation")
    print("=" * 80)
    
    # Install dependencies
    print("\nInstalling dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("Failed to install dependencies.")
        return 1
    
    # Install the package
    print("\nInstalling Code Agent...")
    if args.dev:
        if not run_command("pip install -e ."):
            print("Failed to install Code Agent in development mode.")
            return 1
        print("Code Agent installed in development mode.")
    else:
        if not run_command("pip install ."):
            print("Failed to install Code Agent.")
            return 1
        print("Code Agent installed.")
    
    # Make the CLI script executable
    print("\nMaking CLI script executable...")
    if not run_command("chmod +x code-agent"):
        print("Failed to make CLI script executable.")
        return 1
    
    # Run tests if requested
    if args.test:
        print("\nRunning tests...")
        if not run_command("python tests/test_installation.py"):
            print("Tests failed.")
            return 1
    
    print("\nInstallation complete!")
    print("\nYou can now use Code Agent with:")
    print("  code-agent --help")
    print("  python -m code_agent --help")
    print("  python -m code_agent.demo --help")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

