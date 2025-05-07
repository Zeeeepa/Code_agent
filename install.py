#!/usr/bin/env python3
"""
Installation script for Code Agent
"""

import os
import sys
import subprocess
import argparse
import site
import glob

def run_command(command):
    """Run a shell command and return the output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
        return False
    return True

def find_cli_script():
    """Find the CLI script in various possible locations."""
    possible_locations = []
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    
    # Add potential locations based on environment
    if in_venv:
        # Virtual environment locations
        possible_locations.append(os.path.join(sys.prefix, bin_dir, "code-agent"))
        if sys.platform == "win32":
            possible_locations.append(os.path.join(sys.prefix, bin_dir, "code-agent.exe"))
    else:
        # User site-packages bin directory
        user_bin_dir = site.USER_BASE
        if user_bin_dir:
            user_bin = os.path.join(user_bin_dir, bin_dir, "code-agent")
            possible_locations.append(user_bin)
            if sys.platform == "win32":
                possible_locations.append(user_bin + ".exe")
        
        # System locations
        possible_locations.append(os.path.expanduser("~/.local/bin/code-agent"))
        possible_locations.append("/usr/local/bin/code-agent")
        possible_locations.append("/usr/bin/code-agent")
    
    # Check for entry point scripts in site-packages
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        pattern = os.path.join(site_dir, "code_agent-*.egg-link")
        for egg_link in glob.glob(pattern):
            with open(egg_link, 'r') as f:
                egg_path = f.readline().strip()
                possible_locations.append(os.path.join(egg_path, "code_agent", "runner.py"))
    
    # Check if any of the locations exist
    for location in possible_locations:
        if os.path.exists(location):
            return location
    
    return None

def post_install():
    """Post-installation steps"""
    # Find the CLI script
    cli_path = find_cli_script()
    
    if cli_path:
        print(f"\nFound CLI script at: {cli_path}")
        
        # Make the CLI script executable if it's not on Windows
        if sys.platform != "win32" and not cli_path.endswith(".py"):
            print("Making CLI script executable...")
            if not run_command(f"chmod +x {cli_path}"):
                print(f"Failed to make CLI script executable.")
                return False
            print(f"CLI script made executable.")
    else:
        print("\nCLI script not found in standard locations.")
        print("You can still use the module directly with 'python -m code_agent'")
    
    # Create a simple wrapper script in the current directory if the CLI script wasn't found
    if not cli_path and not os.path.exists("code-agent"):
        print("\nCreating a local wrapper script 'code-agent'...")
        with open("code-agent", "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import sys\n")
            f.write("from code_agent.runner import main\n")
            f.write("\n")
            f.write("if __name__ == \"__main__\":\n")
            f.write("    sys.exit(main())\n")
        
        if sys.platform != "win32":
            run_command("chmod +x code-agent")
        
        print("Created local wrapper script 'code-agent' in the current directory.")
        cli_path = os.path.abspath("code-agent")
    
    print("\nInstallation complete!")
    print("\nYou can now use Code Agent with:")
    if cli_path:
        if cli_path.endswith("runner.py"):
            print(f"  python {cli_path} --help")
        else:
            print(f"  {cli_path} --help")
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
