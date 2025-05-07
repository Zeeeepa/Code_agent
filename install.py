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
        return False, result
    return True, result

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
        user_bin_dir = os.path.expanduser(os.path.join("~", ".local", "bin"))
        user_bin = os.path.join(user_bin_dir, "code-agent")
        system_bin = "/usr/local/bin/code-agent"
        
        if os.path.exists(user_bin):
            cli_path = user_bin
        elif os.path.exists(system_bin):
            cli_path = system_bin
        else:
            cli_path = None
    
    # Make the CLI script executable if it exists
    if cli_path and os.path.exists(cli_path) and sys.platform != "win32":
        print("\nMaking CLI script executable...")
        success, result = run_command(f"chmod +x {cli_path}")
        if not success:
            print(f"Failed to make CLI script executable at {cli_path} due to: {result.stderr}")
            return False
        print(f"CLI script made executable at {cli_path}")
    elif cli_path is None:
        print("\nCLI script not found in any of the expected locations.")
        print("The entry point script may be installed in a different location.")
        print("You may need to manually locate and make it executable.")
    elif sys.platform == "win32":
        if cli_path and os.path.exists(cli_path):
            print(f"\nCLI script found at: {cli_path}")
            print("No need to make executable on Windows.")
        else:
            print("\nCLI script not found in expected location.")
            print("The entry point script may be installed in a different location.")
    else:
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
    success, _ = run_command("python tests/test_installation.py")
    if not success:
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
    success, _ = run_command("pip install -r requirements.txt")
    if not success:
        print("Failed to install dependencies.")
        sys.exit(1)
    
    # Install the package
    print("\nInstalling Code Agent...")
    if args.dev:
        success, _ = run_command("pip install -e .")
        if not success:
            print("Failed to install Code Agent in development mode.")
            sys.exit(1)
        print("Code Agent installed in development mode.")
    else:
        success, _ = run_command("pip install .")
        if not success:
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
