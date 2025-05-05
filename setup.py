#!/usr/bin/env python3
"""
Setup script for Code Agent
Combines functionality from both setup.py and install.py
"""

import os
import sys
import subprocess
from setuptools import setup, find_packages
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
    # Make the CLI script executable
    print("\nMaking CLI script executable...")
    if not run_command("chmod +x code-agent"):
        print("Failed to make CLI script executable.")
        return False
    
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

# Handle command line arguments if script is run directly
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

# Setup configuration for pip install
setup(
    name="code_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "codegen>=0.1.0",
        "PyGithub>=1.55",
        "pyngrok>=5.1.0",
        "requests>=2.25.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=20.8b1",
            "flake8>=3.8.0",
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "code-agent=code_agent.runner:main",
        ],
    },
    python_requires=">=3.7",
    description="AI-powered code agent for GitHub repositories",
    author="Zeeeepa",
    author_email="info@zeeeepa.com",
    url="https://github.com/Zeeeepa/Code_agent",
    # Add custom commands for post-install
    cmdclass={
        # Custom commands could be added here if needed
    },
)
