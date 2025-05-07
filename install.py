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

def post_install():
    """Post-installation steps"""
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    
    # Determine the path to the CLI script
    if in_venv:
        cli_path = os.path.join(sys.prefix, bin_dir, "code-agent")
        if sys.platform == "win32":
            cli_path += ".exe"
    else:
        # Try to find in user's bin directory
        user_bin = os.path.expanduser("~/.local/bin/code-agent")
        system_bin = "/usr/local/bin/code-agent"
        cli_path = user_bin if os.path.exists(user_bin) else system_bin
    
    # Make the CLI script executable if it exists
    if os.path.exists(cli_path) and sys.platform != "win32":
        print("\nMaking CLI script executable...")
        if not run_command(f"chmod +x {cli_path}"):
            print(f"Failed to make CLI script executable at {cli_path}.")
            return False
        print(f"CLI script made executable at {cli_path}")
    elif sys.platform != "win32":
        print(f"\nCLI script not found at expected location: {cli_path}")
        print("The entry point script may be installed in a different location.")
        print("You may need to manually locate and make it executable.")
    
    print("\nInstallation complete!")
    print("\nYou can now use Code Agent with:")
    print("  code-agent --help")
    print("  python -m code_agent --help")
    print("  python -m code_agent.demo --help")
    
    return True

def run_tests():
    """Run the installation tests"""
    print("\nRunning tests...")
    if not run_command("python tests/test_installation.py"):
        print("Tests failed.")
        return False
    return True

if __name__ == "__main__":
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
        sys.exit(1)
    
    # Install the package
    print("\nInstalling Code Agent...")
    if args.dev:
        if not run_command("pip install -e ."):
            print("Failed to install Code Agent in development mode.")
            sys.exit(1)
        print("Code Agent installed in development mode.")
    else:
        if not run_command("pip install ."):
            print("Failed to install Code Agent.")
            sys.exit(1)
        print("Code Agent installed.")
    
    # Post-installation steps
    if not post_install():
        sys.exit(1)
    
    # Run tests if requested
    if args.test and not run_tests():
        sys.exit(1)
    
    sys.exit(0)
