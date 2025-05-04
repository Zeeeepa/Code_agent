#!/usr/bin/env python3
"""
CodeGen Runner

This script integrates the three main components of the CodeGen workflow system.
It's renamed from codegen_runner.py to agent_runner.py to avoid circular imports.
"""

import os
import sys
import argparse
import importlib.util
from pathlib import Path

def load_module(file_path, module_name):
    """Dynamically load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CodeGen Integration Runner")
    parser.add_argument(
        "--mode", 
        choices=["issue", "context", "workflow"], 
        required=True,
        help="Mode to run: issue (solve a GitHub issue), context (manage context), workflow (run CI/CD workflow)"
    )
    
    # First parse just the mode to determine which additional arguments to add
    args, remaining = parser.parse_known_args()
    
    # Add additional arguments based on the mode
    if args.mode == "issue":
        parser.add_argument("--issue-number", type=int, required=True, help="GitHub issue number")
        parser.add_argument("--task-type", default="bug", 
                        choices=["bug", "feature", "documentation", "code_review", "refactoring"], 
                        help="Type of task (default: bug)")
        parser.add_argument("--org-id", help="CodeGen organization ID (can also use CODEGEN_ORG_ID env var)")
        parser.add_argument("--token", help="CodeGen API token (can also use CODEGEN_TOKEN env var)")
    
    elif args.mode == "context":
        subparsers = parser.add_subparsers(dest="command", help="Command to run")
        
        # Collect command
        collect_parser = subparsers.add_parser("collect", help="Collect context")
        collect_parser.add_argument("--output", "-o", default="context.json", help="Output file")
        collect_parser.add_argument("--issue", "-i", type=int, help="Issue number")
        collect_parser.add_argument("--pr", "-p", type=int, help="PR number")
        collect_parser.add_argument("--max-files", type=int, default=20, help="Maximum number of files to include")
        collect_parser.add_argument("--file-patterns", nargs="+", help="File patterns to include")
        collect_parser.add_argument("--exclude-patterns", nargs="+", help="Patterns to exclude")
        
        # Generate prompt command
        prompt_parser = subparsers.add_parser("prompt", help="Generate a CodeGen prompt")
        prompt_parser.add_argument("--input", "-i", default="context.json", help="Input context file")
        prompt_parser.add_argument("--output", "-o", help="Output file (if not provided, print to stdout)")
        prompt_parser.add_argument("--task-type", "-t", default="feature", 
                               choices=["bug", "feature", "documentation", "code_review", "refactoring"],
                               help="Type of task")
    
    elif args.mode == "workflow":
        parser.add_argument("--github-token", help="GitHub API token")
        parser.add_argument("--ngrok-token", help="ngrok authentication token")
        parser.add_argument("--repo-name", help="GitHub repository name (format: owner/repo)")
        parser.add_argument("--codegen-token", help="CodeGen API token")
        parser.add_argument("--codegen-org-id", help="CodeGen organization ID")
        parser.add_argument("--webhook-port", type=int, default=5000, help="Port for webhook server (default: 5000)")
    
    # Parse all arguments
    args = parser.parse_args()
    
    # Load the appropriate module based on the mode
    try:
        script_dir = Path(__file__).resolve().parent
        
        if args.mode == "issue":
            issue_solver = load_module(script_dir / "codegen_issue_solver.py", "issue_solver")
            
            # Get credentials from args or environment variables
            org_id = args.org_id or os.environ.get("CODEGEN_ORG_ID")
            token = args.token or os.environ.get("CODEGEN_TOKEN")
            
            if not org_id or not token:
                print("Error: CodeGen organization ID and token are required.")
                print("Provide them as arguments or set CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables.")
                sys.exit(1)
            
            # Solve the issue
            task_id = issue_solver.solve_issue(args.issue_number, args.task_type, org_id, token)
            
            if task_id:
                print(f"Issue #{args.issue_number} is being processed by CodeGen.")
                print(f"You can check the progress at: https://app.codegen.com/tasks/{task_id}")
            else:
                print(f"Failed to process issue #{args.issue_number}.")
                sys.exit(1)
                
        elif args.mode == "context":
            context_manager = load_module(script_dir / "context_manager.py", "context_manager")
            
            # Create a list of arguments for the context manager
            sys.argv = [sys.argv[0]] + [args.command] + remaining
            context_manager.main()
            
        elif args.mode == "workflow":
            # We'll rename this to avoid circular imports
            workflow = load_module(script_dir / "codegen.py", "workflow")
            
            # Directly use the main function from the workflow module
            # Convert the args namespace to a list to pass to the workflow main function
            sys.argv = [sys.argv[0]] + remaining
            workflow.main()
            
    except Exception as e:
        print(f"Error running {args.mode} mode: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()