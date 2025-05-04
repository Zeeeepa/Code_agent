#!/usr/bin/env python3
"""
Code Agent Integration Demo

This script demonstrates the integration of all three Code Agent components:
1. Issue Solver
2. Context Manager 
3. CI/CD Workflow

It shows a complete workflow from collecting context to solving issues
and automating development.
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

# Import our configuration
from code_agent.core.config import get_config, init_config_from_args

def run_command(command):
    """Run a shell command and return the output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
    return result.stdout

def main():
    parser = argparse.ArgumentParser(description="Code Agent Integration Demo")
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/repo)")
    parser.add_argument("--issue", type=int, required=True, help="GitHub issue number to solve")
    parser.add_argument("--codegen-token", help="CodeGen API token")
    parser.add_argument("--codegen-org-id", help="CodeGen organization ID")
    parser.add_argument("--github-token", help="GitHub token")
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = init_config_from_args(args)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    
    print("=" * 80)
    print("Code Agent Integration Demo")
    print("=" * 80)
    
    # Step 1: Collect context using Context Manager
    print("\n[Step 1] Collecting context...")
    context_cmd = f"python -m code_agent.runner --mode context collect --issue {args.issue} --output context_{args.issue}.json"
    result = run_command(context_cmd)
    print(f"Context collection complete. Output: context_{args.issue}.json")
    
    # Step 2: Solve the issue using Issue Solver
    print("\n[Step 2] Solving the issue...")
    issue_cmd = f"python -m code_agent.runner --mode issue --issue-number {args.issue} --task-type bug"
    result = run_command(issue_cmd)
    print("Issue solving initiated.")
    
    # Step 3: Simulate waiting for the CodeGen task to complete
    print("\n[Step 3] Waiting for CodeGen task to complete...")
    for i in range(5):
        print(f"  Still working... ({i+1}/5)")
        time.sleep(2)
    print("CodeGen task completed (simulated).")
    
    # Step 4: Start the workflow to implement the solution
    print("\n[Step 4] Starting CI/CD workflow...")
    workflow_cmd = f"python -m code_agent.runner --mode workflow --repo-name {args.repo}"
    result = run_command(workflow_cmd)
    print("CI/CD workflow started. Press Ctrl+C to stop.")
    
    print("\nDemo workflow complete!")

if __name__ == "__main__":
    main()
