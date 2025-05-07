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

def get_virtualenv_locations():
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    locations = [os.path.join(sys.prefix, bin_dir, "code-agent")]
    if sys.platform == "win32":
        locations.append(os.path.join(sys.prefix, bin_dir, "code-agent.exe"))
    return locations

def get_system_locations():
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    locations = []
    import site
    user_base = site.USER_BASE
    if user_base:
        user_bin = os.path.join(user_base, bin_dir, "code-agent")
        locations.append(user_bin)
        if sys.platform == "win32":
            locations.append(user_bin + ".exe")
    locations.extend([
        os.path.expanduser("~/.local/bin/code-agent"),
        "/usr/local/bin/code-agent",
        "/usr/bin/code-agent"
    ])
    return locations

def get_egg_link_locations():
    locations = []
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        pattern = os.path.join(site_dir, "code_agent-*.egg-link")
        for egg_link in glob.glob(pattern):
            try:
                with open(egg_link, 'r') as f:
                    egg_path = f.readline().strip()
                    # Verify the path exists and is a directory before adding it
                    if egg_path and os.path.isdir(egg_path):
                        locations.append(os.path.join(egg_path, "code_agent", "runner.py"))
            except (IOError, OSError) as e:
                # Skip this egg-link if there's an error reading it
                print(f"Warning: Could not read egg-link file {egg_link}: {e}")
                continue
    return locations

def find_cli_script():
    """Find the CLI script in various possible locations."""
    possible_locations = []
    in_venv = sys.prefix != sys.base_prefix
    possible_locations.extend(get_virtualenv_locations() if in_venv else get_system_locations())
    possible_locations.extend(get_egg_link_locations())
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
            try:
                if not run_command(f"chmod +x {cli_path}"):
                    raise Exception(f"Failed to make CLI script executable: {cli_path}")
                print(f"CLI script made executable.")
            except Exception as e:
                print(f"Error making CLI script executable: {e}")
                return False
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
            try:
                if not run_command("chmod +x code-agent"):
                    raise Exception("Failed to make local wrapper script executable")
                print("Made local wrapper script executable.")
            except Exception as e:
                print(f"Error making local wrapper script executable: {e}")
                return False
        
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
