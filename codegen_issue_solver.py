"""
Codegen Issue Solver
This script demonstrates how to use the Codegen API to solve GitHub issues.
It collects context about an issue, generates a prompt, and sends it to the Codegen API.
Usage:
    python codegen_issue_solver.py --issue-number 123 --task-type bug
"""
import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
try:
    from codegen import Agent
except ImportError:
    print("Codegen SDK not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "codegen"])
    from codegen import Agent
class IssueContext:
    """Collects and manages context for a GitHub issue."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize with the repository path."""
        self.repo_path = Path(repo_path)
        self.context = {
            "repository": "",
            "issue": {},
            "code_snippets": [],
            "error_logs": []
        }
    
    def collect_repo_info(self) -> None:
        """Collect basic repository information."""
        try:
            # Get repository name from git remote
            remote_url = self._run_command("git config --get remote.origin.url")
            if remote_url:
                # Extract owner/repo from URL
                if "github.com" in remote_url:
                    parts = remote_url.strip().split("github.com/")
                    if len(parts) > 1:
                        repo_path = parts[1].replace(".git", "").strip()
                        self.context["repository"] = repo_path
            
            # Get branch name
            branch = self._run_command("git rev-parse --abbrev-ref HEAD").strip()
            self.context["branch"] = branch
            
        except Exception as e:
            print(f"Error collecting repository info: {e}")
    
    def collect_issue_info(self, issue_number: int) -> None:
        """Collect information about a GitHub issue."""
        try:
            # Check if GitHub CLI is available
            if self._command_exists("gh"):
                # Get issue details using GitHub CLI
                issue_json = self._run_command(f"gh issue view {issue_number} --json title,body,labels,assignees,comments")
                if issue_json:
                    issue_data = json.loads(issue_json)
                    self.context["issue"] = issue_data
                    print(f"Collected info for issue #{issue_number}: {issue_data.get('title', 'Unknown')}")
                else:
                    print(f"Failed to get data for issue #{issue_number}")
            else:
                print("GitHub CLI not found. Install it for better issue context.")
                self.context["issue"] = {
                    "number": issue_number,
                    "title": "Unknown issue",
                    "body": "Could not fetch issue details - GitHub CLI not available"
                }
        except Exception as e:
            print(f"Error collecting issue info: {e}")
    
    def find_relevant_code(self, keywords: list) -> None:
        """Find code snippets related to the issue based on keywords."""
        try:
            # Use grep to find code containing the keywords
            file_types = [
                "--include=*.py", 
                "--include=*.js", 
                "--include=*.ts", 
                "--include=*.jsx", 
                "--include=*.tsx",
                "--include=*.go",
                "--include=*.java",
                "--include=*.rb"
            ]
            
            # Create a combined grep pattern
            pattern = "|".join(keywords)
            grep_command = f"grep -r {' '.join(file_types)} -l -E '{pattern}' ."
            
            # Run the grep command
            files = self._run_command(grep_command).strip().split("\n")
            files = [f for f in files if f and not f.startswith("./node_modules/") and not f.startswith("./venv/")]
            
            # Limit to 5 most relevant files
            for file_path in files[:5]:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    self.context["code_snippets"].append({
                        "file": file_path,
                        "content": content
                    })
                except Exception as file_error:
                    print(f"Error reading file {file_path}: {file_error}")
            
            print(f"Found {len(self.context['code_snippets'])} relevant code files")
            
        except Exception as e:
            print(f"Error finding relevant code: {e}")
    
    def find_error_logs(self) -> None:
        """Find error logs in the repository."""
        try:
            # Look for log files
            log_files = self._run_command("find . -name '*.log' -type f").strip().split("\n")
            log_files = [f for f in log_files if f and not f.startswith("./node_modules/") and not f.startswith("./venv/")]
            
            # Look for errors in log files
            for log_file in log_files[:3]:  # Limit to 3 log files
                try:
                    # Use grep to find error lines
                    error_lines = self._run_command(f"grep -i 'error|exception|fail|crash' {log_file} | tail -50")
                    if error_lines.strip():
                        self.context["error_logs"].append({
                            "file": log_file,
                            "content": error_lines
                        })
                except Exception as log_error:
                    print(f"Error processing log file {log_file}: {log_error}")
            
            print(f"Found {len(self.context['error_logs'])} log files with errors")
            
        except Exception as e:
            print(f"Error finding error logs: {e}")
    
    def extract_keywords(self) -> list:
        """Extract keywords from the issue title and body."""
        keywords = []
        
        # Get issue title and body
        title = self.context.get("issue", {}).get("title", "")
        body = self.context.get("issue", {}).get("body", "")
        
        # Extract keywords from title
        if title:
            # Split by spaces and punctuation
            title_words = ''.join(c if c.isalnum() else ' ' for c in title).split()
            # Filter out short words and common words
            title_keywords = [w.lower() for w in title_words if len(w) > 3 and w.lower() not in 
                             ("the", "and", "that", "this", "with", "from", "have", "for")]
            keywords.extend(title_keywords)
        
        # Extract keywords from body
        if body:
            # Look for code blocks or technical terms
            import re
            # Find words that look like code (camelCase, snake_case, etc.)
            code_like = re.findall(r'\b[a-zA-Z]+(?:[A-Z][a-z]+)+\b|\b[a-z]+(?:_[a-z]+)+\b', body)
            keywords.extend([w.lower() for w in code_like])
            
            # Find error messages often in quotes or code blocks
            error_msgs = re.findall(r'`([^`]+)`|```[^\n]*([^`]+)```', body)
            for match in error_msgs:
                for group in match:
                    if group:
                        # Take the first line which is often the error message
                        error_line = group.strip().split('\n')[0]
                        keywords.append(error_line)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        for kw in keywords:
            if kw and kw not in unique_keywords:
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to 10 keywords
    
    def create_prompt(self, task_type: str) -> str:
        """Create a prompt for the Codegen API based on the collected context."""
        # Repository information
        repository = self.context.get("repository", "Unknown")
        branch = self.context.get("branch", "main")
        
        # Issue information
        issue = self.context.get("issue", {})
        issue_number = issue.get("number", "Unknown")
        issue_title = issue.get("title", "Unknown issue")
        issue_body = issue.get("body", "No description provided")
        
        # Task-specific instructions
        task_instructions = {
            "bug": """
            ## Bug Fix Task
            
            Please analyze the information about this bug and:
            
            1. Identify the root cause of the bug
            2. Develop a fix for the issue
            3. Provide a detailed explanation of your solution
            4. Create a PR with your changes
            """,
            
            "feature": """
            ## Feature Implementation Task
            
            Please implement the requested feature:
            
            1. Design an approach for the feature
            2. Implement the feature following project patterns
            3. Add appropriate tests
            4. Create a PR with your implementation
            """,
            
            "documentation": """
            ## Documentation Task
            
            Please improve the documentation as requested:
            
            1. Analyze the documentation needs
            2. Create or update documentation
            3. Ensure it's clear, concise, and well-structured
            4. Create a PR with your documentation changes
            """,
            
            "code_review": """
            ## Code Review Task
            
            Please review the code and provide feedback:
            
            1. Analyze the code for bugs, performance issues, and style
            2. Suggest improvements
            3. Implement fixes for any issues found
            4. Create a PR with your changes
            """,
            
            "refactoring": """
            ## Code Refactoring Task
            
            Please refactor the code as needed:
            
            1. Identify code that needs improvement
            2. Implement refactoring changes
            3. Ensure functionality is preserved
            4. Create a PR with your refactoring
            """
        }
        
        # Default instructions if task type not found
        if task_type not in task_instructions:
            task_instructions[task_type] = f"""
            ## {task_type.title()} Task
            
            Please address this {task_type} request:
            
            1. Analyze the context provided
            2. Implement an appropriate solution
            3. Create a PR with your changes
            """
        
        # Code snippet information
        code_context = ""
        if self.context.get("code_snippets"):
            code_context = "## Relevant Code Files\n"
            for i, snippet in enumerate(self.context["code_snippets"]):
                file_path = snippet.get("file", f"Unknown file {i}")
                content = snippet.get("content", "No content")
                # Truncate very long files
                if len(content) > 2000:
                    content = content[:2000] + "... (truncated)"
                code_context += f"### {file_path}\n```\n{content}\n```\n\n"
        
        # Error log information
        error_context = ""
        if self.context.get("error_logs"):
            error_context = "## Error Logs\n"
            for i, log in enumerate(self.context["error_logs"]):
                file_path = log.get("file", f"Unknown log {i}")
                content = log.get("content", "No content")
                error_context += f"### {file_path}\n{content}\n\n"
        
        # Build the complete prompt
        prompt = f"""
        # {task_type.title()} Task for {repository}
        
        ## Issue Information
        - Repository: {repository} (branch: {branch})
        - Issue: #{issue_number} - {issue_title}
        
        ## Issue Description
        {issue_body}
        
        {task_instructions[task_type]}
        
        {code_context}
        {error_context}
        
        ## Final Instructions
        
        Please implement your solution and create a pull request. Be sure to:
        - Explain your approach and reasoning
        - Test your changes thoroughly 
        - Follow the project's style and conventions
        """
        
        return prompt
    
    def save_context(self, filename: str) -> None:
        """Save the collected context to a file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2)
            print(f"Context saved to {filename}")
        except Exception as e:
            print(f"Error saving context: {e}")
    
    def _run_command(self, command: str) -> str:
        """Run a shell command and return the output."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=False,  # Don't raise an exception if command fails
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout
        except Exception as e:
            print(f"Command error: {e}")
            return ""
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in the system."""
        try:
            subprocess.run(
                ["which", command], 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
def solve_issue(issue_number: int, task_type: str, org_id: str, token: str) -> Optional[str]:
    """Solve a GitHub issue using the Codegen API.
    
    Args:
        issue_number: GitHub issue number
        task_type: Type of task (bug, feature, etc.)
        org_id: Codegen organization ID
        token: Codegen API token
        
    Returns:
        URL to the Codegen task, or None if failed
    """
    print(f"Starting issue solver for issue #{issue_number}")
    
    # Create context collector
    context = IssueContext()
    
    # Collect repository info
    print("Collecting repository info...")
    context.collect_repo_info()
    
    # Collect issue info
    print(f"Collecting info for issue #{issue_number}...")
    context.collect_issue_info(issue_number)
    
    # Extract keywords from issue
    keywords = context.extract_keywords()
    print(f"Extracted keywords: {', '.join(keywords)}")
    
    # Find relevant code based on keywords
    print("Finding relevant code...")
    context.find_relevant_code(keywords)
    
    # Find error logs
    print("Finding error logs...")
    context.find_error_logs()
    
    # Save context to a file
    context.save_context(f"issue_{issue_number}_context.json")
    
    # Create prompt
    print(f"Creating prompt for {task_type} task...")
    prompt = context.create_prompt(task_type)
    
    # Save prompt to a file
    prompt_file = f"issue_{issue_number}_prompt.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"Prompt saved to {prompt_file}")
    
    # Initialize Codegen agent
    print(f"Initializing Codegen agent with org_id={org_id}")
    try:
        # Initialize the Agent with the organization ID and token
        agent = Agent(org_id=org_id, token=token)
        
        # Run the agent with the prompt
        print("Creating Codegen task...")
        task = agent.run(prompt=prompt)
        
        # Print task information
        print(f"Task created with ID: {task.id}")
        print(f"Initial status: {task.status}")
        
        # Monitor task status
        max_retries = 30
        for i in range(max_retries):
            # Refresh task status
            task.refresh()
            
            if task.status == "completed":
                print(f"Task completed successfully!")
                return task.id
            elif task.status == "failed":
                print(f"Task failed: {task.error}")
                return None
            else:
                print(f"Task status: {task.status}. Waiting...")
                time.sleep(10)  # Wait 10 seconds before checking again
        
        print("Task timed out. Please check the Codegen dashboard for status.")
        return task.id
    except Exception as e:
        print(f"Error running Codegen agent: {e}")
        return None
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve GitHub issues using Codegen")
    parser.add_argument("--issue-number", type=int, required=True, help="GitHub issue number")
    parser.add_argument("--task-type", default="bug", choices=["bug", "feature", "documentation", "code_review", "refactoring"], 
                        help="Type of task (default: bug)")
    parser.add_argument("--org-id", help="Codegen organization ID (can also use CODEGEN_ORG_ID env var)")
    parser.add_argument("--token", help="Codegen API token (can also use CODEGEN_TOKEN env var)")
    
    args = parser.parse_args()
    
    # Get credentials from args or environment variables
    org_id = args.org_id or os.environ.get("CODEGEN_ORG_ID")
    token = args.token or os.environ.get("CODEGEN_TOKEN")
    
    if not org_id or not token:
        print("Error: Codegen organization ID and token are required.")
        print("Provide them as arguments or set CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables.")
        sys.exit(1)
    
    # Solve the issue
    task_id = solve_issue(args.issue_number, args.task_type, org_id, token)
    
    if task_id:
        print(f"Issue #{args.issue_number} is being processed by Codegen.")
        print(f"You can check the progress at: https://app.codegen.com/tasks/{task_id}")
    else:
        print(f"Failed to process issue #{args.issue_number}.")
        sys.exit(1)
