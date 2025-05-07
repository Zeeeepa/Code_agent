#!/usr/bin/env python3
"""
Code Agent Interactive Launcher

This script provides an interactive menu to launch different Code Agent modes:
1. Full Test Launch - Runs all tests to verify the installation
2. Demo Launch - Runs the demo with a sample GitHub project
3. Advanced Example - Runs with an actual GitHub project selected by the user

Usage:
    python start.py
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header."""
    clear_screen()
    print("=" * 80)
    print("Code Agent Interactive Launcher".center(80))
    print("=" * 80)
    print("\nWelcome to Code Agent - AI-powered GitHub issue solver and workflow automation\n")

def run_command(command, capture_output=True):
    """Run a shell command and optionally return the output."""
    print(f"Running: {command}")
    if capture_output:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"Command failed with error: {result.stderr}")
        return result.stdout
    else:
        # Run without capturing output (shows in real-time)
        subprocess.run(command, shell=True, text=True)
        return None

def check_environment():
    """Check if required environment variables are set."""
    required_vars = {
        "CODEGEN_TOKEN": "CodeGen API token",
        "CODEGEN_ORG_ID": "CodeGen organization ID",
        "GITHUB_TOKEN": "GitHub token"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        print("\n⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in a .env file or in your environment.")
        print("You can use the .env.example file as a template.")
        
        # Ask if user wants to continue anyway
        response = input("\nDo you want to continue anyway? (y/n): ").strip().lower()
        return response == 'y'
    
    return True

def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_path = Path('.env')
    if env_path.exists():
        print("Loading environment variables from .env file...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        return True
    else:
        print("No .env file found. Using existing environment variables.")
        return False

def run_tests():
    """Run all tests to verify the installation."""
    print_header()
    print("Running all tests to verify the installation...\n")
    
    # Run the tests
    run_command("python run_tests.py", capture_output=False)
    
    input("\nPress Enter to return to the main menu...")

def run_demo():
    """Run the demo with user-provided or sample values."""
    print_header()
    print("Running the Code Agent Demo\n")
    
    # Get repository and issue information
    repo = input("Enter GitHub repository (owner/repo) or press Enter for example: ").strip()
    if not repo:
        repo = "Zeeeepa/Code_agent"  # Default example repository
    
    issue = input("Enter GitHub issue number or press Enter for example: ").strip()
    if not issue:
        issue = "1"  # Default example issue
    
    # Run the demo
    print(f"\nStarting demo with repository: {repo} and issue: {issue}\n")
    demo_cmd = f"python -m code_agent.demo --repo {repo} --issue {issue}"
    
    try:
        run_command(demo_cmd, capture_output=False)
    except KeyboardInterrupt:
        print("\nDemo stopped by user.")
    
    input("\nPress Enter to return to the main menu...")

def run_advanced_example():
    """Run with an actual GitHub project selected by the user."""
    print_header()
    print("Advanced Example - Run with a specific GitHub project\n")
    
    # Get repository information
    repo = input("Enter GitHub repository (owner/repo): ").strip()
    if not repo:
        print("Repository name is required.")
        input("\nPress Enter to return to the main menu...")
        return
    
    # Choose the mode
    print("\nSelect a mode:")
    print("1. Issue Solver - Solve a GitHub issue")
    print("2. Context Manager - Collect context for an issue")
    print("3. Workflow - Run CI/CD workflow")
    
    mode_choice = input("\nEnter your choice (1-3): ").strip()
    
    if mode_choice == "1":
        # Issue Solver mode
        issue_number = input("Enter GitHub issue number: ").strip()
        if not issue_number:
            print("Issue number is required.")
            input("\nPress Enter to return to the main menu...")
            return
        
        task_types = ["bug", "feature", "documentation", "code_review", "refactoring"]
        print("\nSelect task type:")
        for i, task_type in enumerate(task_types, 1):
            print(f"{i}. {task_type}")
        
        task_choice = input("\nEnter your choice (1-5): ").strip()
        try:
            task_type = task_types[int(task_choice) - 1]
        except (ValueError, IndexError):
            task_type = "bug"  # Default
        
        cmd = f"python -m code_agent.runner --mode issue --issue-number {issue_number} --task-type {task_type}"
    
    elif mode_choice == "2":
        # Context Manager mode
        print("\nSelect context command:")
        print("1. Collect context")
        print("2. Generate prompt")
        
        context_choice = input("\nEnter your choice (1-2): ").strip()
        
        if context_choice == "1":
            issue = input("Enter GitHub issue number (optional): ").strip()
            output = input("Enter output file (default: context.json): ").strip() or "context.json"
            
            cmd = f"python -m code_agent.runner --mode context collect --output {output}"
            if issue:
                cmd += f" --issue {issue}"
        
        elif context_choice == "2":
            input_file = input("Enter input context file (default: context.json): ").strip() or "context.json"
            output = input("Enter output file (optional, leave empty for stdout): ").strip()
            
            cmd = f"python -m code_agent.runner --mode context prompt --input {input_file}"
            if output:
                cmd += f" --output {output}"
        
        else:
            print("Invalid choice.")
            input("\nPress Enter to return to the main menu...")
            return
    
    elif mode_choice == "3":
        # Workflow mode
        cmd = f"python -m code_agent.runner --mode workflow --repo-name {repo}"
    
    else:
        print("Invalid choice.")
        input("\nPress Enter to return to the main menu...")
        return
    
    # Run the command
    print(f"\nRunning: {cmd}\n")
    try:
        run_command(cmd, capture_output=False)
    except KeyboardInterrupt:
        print("\nCommand stopped by user.")
    
    input("\nPress Enter to return to the main menu...")

def main_menu():
    """Display the main menu and handle user input."""
    while True:
        print_header()
        print("Select an option:")
        print("1. Full Test Launch - Run all tests to verify the installation")
        print("2. Demo Launch - Run the demo with a sample GitHub project")
        print("3. Advanced Example - Run with an actual GitHub project selected by the user")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            run_tests()
        elif choice == "2":
            run_demo()
        elif choice == "3":
            run_advanced_example()
        elif choice == "4":
            print("\nExiting Code Agent. Goodbye!")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please try again.")
            time.sleep(1)

def main():
    """Main entry point."""
    # Load environment variables from .env file if it exists
    load_env_file()
    
    # Check if required environment variables are set
    if not check_environment():
        print("\nExiting due to missing environment variables.")
        sys.exit(1)
    
    # Display the main menu
    main_menu()

if __name__ == "__main__":
    main()

