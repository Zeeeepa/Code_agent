#!/usr/bin/env python
"""
Context Manager for Codegen Workflows
This utility helps collect, manage, and pass context between GitHub Actions workflows
and Codegen API calls, ensuring rich context for AI agents to work with.
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
class CodegenContext:
    """Manages context collection and handling for Codegen API calls."""
    
    def __init__(self, base_dir: str = "."):
        """Initialize the context manager.
        
        Args:
            base_dir: Base directory for context collection
        """
        self.base_dir = Path(base_dir)
        self.context_data: Dict[str, Any] = {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "metadata": {},
            "files": {},
            "issues": [],
            "codebase": {}
        }
        
        # Create a directory for temporary context files
        self.context_dir = self.base_dir / ".context"
        self.context_dir.mkdir(exist_ok=True)
    
    def collect_repo_metadata(self) -> None:
        """Collect repository metadata."""
        try:
            # Get repository information
            self.context_data["metadata"]["owner"] = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
            self.context_data["metadata"]["repo"] = os.environ.get("GITHUB_REPOSITORY", "").split("/")[-1] if "/" in os.environ.get("GITHUB_REPOSITORY", "") else ""
            self.context_data["metadata"]["default_branch"] = self._run_command("git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'").strip()
            
            # Get programming languages used
            file_extensions = self._run_command("git ls-files | grep -v '^\\.' | grep -o '\\.[^.]*$' | sort | uniq -c | sort -nr").strip()
            self.context_data["metadata"]["languages"] = [line.strip().split()[-1][1:] for line in file_extensions.split("\n") if line.strip()]
            
            # Get commit statistics
            self.context_data["metadata"]["commit_count"] = int(self._run_command("git rev-list --count HEAD").strip())
            
            # Get contributor list
            contributors = self._run_command("git log --format='%an' | sort | uniq").strip()
            self.context_data["metadata"]["contributors"] = [c for c in contributors.split("\n") if c.strip()]
            
            # Get repository structure
            dir_structure = self._run_command(
                "find . -type d -not -path '*/\\.*' -not -path '*/node_modules/*' -not -path '*/venv/*' -maxdepth 3"
            ).strip()
            self.context_data["metadata"]["directory_structure"] = [d[2:] for d in dir_structure.split("\n") if d.strip() and d != "."]
            
        except Exception as e:
            print(f"Error collecting repository metadata: {e}")
    
    def collect_issue_data(self, issue_number: int) -> None:
        """Collect data about a specific issue.
        
        Args:
            issue_number: GitHub issue number
        """
        try:
            # Check if we have the GitHub CLI available
            if self._command_exists("gh"):
                # Try to get issue details
                issue_data = self._run_command(f"gh issue view {issue_number} --json title,body,labels,assignees")
                self.context_data["issues"].append(json.loads(issue_data))
                
                # Get issue comments
                comments_data = self._run_command(f"gh issue view {issue_number} --json comments")
                comments = json.loads(comments_data).get("comments", [])
                self.context_data["issues"][-1]["comments"] = comments
        except Exception as e:
            print(f"Error collecting issue data: {e}")
    
    def collect_pr_data(self, pr_number: int) -> None:
        """Collect data about a specific pull request.
        
        Args:
            pr_number: GitHub PR number
        """
        try:
            # Check if we have the GitHub CLI available
            if self._command_exists("gh"):
                # Try to get PR details
                pr_data = self._run_command(f"gh pr view {pr_number} --json title,body,labels,assignees,files,commits")
                pr_info = json.loads(pr_data)
                self.context_data["pull_requests"] = [pr_info]
                
                # Get PR diff
                pr_diff = self._run_command(f"gh pr diff {pr_number}")
                self.context_data["pull_requests"][-1]["diff"] = pr_diff
                
                # Get PR comments
                comments_data = self._run_command(f"gh pr view {pr_number} --json comments,reviews")
                comments = json.loads(comments_data)
                self.context_data["pull_requests"][-1]["comments"] = comments.get("comments", [])
                self.context_data["pull_requests"][-1]["reviews"] = comments.get("reviews", [])
        except Exception as e:
            print(f"Error collecting PR data: {e}")
    
    def collect_code_context(self, 
                            file_patterns: List[str] = None, 
                            max_files: int = 20, 
                            exclude_patterns: List[str] = None) -> None:
        """Collect context from code files.
        
        Args:
            file_patterns: List of glob patterns to include (e.g., ["*.py", "*.js"])
            max_files: Maximum number of files to include
            exclude_patterns: List of patterns to exclude (e.g., ["*test*", "*mock*"])
        """
        try:
            # Default patterns if none provided
            if file_patterns is None:
                file_patterns = ["*.py", "*.js", "*.ts", "*.go", "*.java", "*.rb", "*.c", "*.cpp", "*.h", "*.hpp"]
            
            # Default exclude patterns if none provided
            if exclude_patterns is None:
                exclude_patterns = ["*test*", "*node_modules*", "*venv*", "*dist*", "*build*"]
            
            # Build find command
            find_cmd = ["find", ".", "-type", "f"]
            
            # Add include patterns
            for pattern in file_patterns:
                find_cmd.extend(["-o", "-name", pattern])
            
            # Add exclude patterns
            for pattern in exclude_patterns:
                find_cmd.extend(["-not", "-path", pattern])
            
            # Run the command
            files_output = self._run_command(" ".join(find_cmd))
            files = [f[2:] for f in files_output.split("\n") if f.strip()]
            
            # Limit number of files
            files = files[:max_files]
            
            # Read file contents
            for file_path in files:
                try:
                    full_path = self.base_dir / file_path
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    # Add to context
                    self.context_data["files"][file_path] = {
                        "content": content,
                        "size_bytes": os.path.getsize(full_path),
                        "last_modified": os.path.getmtime(full_path)
                    }
                except Exception as file_error:
                    print(f"Error reading file {file_path}: {file_error}")
            
        except Exception as e:
            print(f"Error collecting code context: {e}")
    
    def analyze_codebase(self) -> None:
        """Analyze the codebase for important structural patterns."""
        try:
            # Count files by type
            file_types = {}
            for file_path in self.context_data["files"]:
                ext = os.path.splitext(file_path)[1]
                if ext not in file_types:
                    file_types[ext] = 0
                file_types[ext] += 1
            
            self.context_data["codebase"]["file_types"] = file_types
            
            # Look for important patterns - entry points, etc.
            self.context_data["codebase"]["entry_points"] = []
            
            for file_path, file_info in self.context_data["files"].items():
                content = file_info["content"]
                
                # Check for common entry points
                if "main(" in content or "if __name__ == \"__main__\"" in content:
                    self.context_data["codebase"]["entry_points"].append(file_path)
                
            # Check for common config files
            common_configs = ["package.json", "setup.py", "pyproject.toml", "requirements.txt", 
                             ".pre-commit-config.yaml", "Dockerfile", "docker-compose.yml"]
            
            self.context_data["codebase"]["config_files"] = [f for f in common_configs 
                                                         if os.path.exists(self.base_dir / f)]
            
        except Exception as e:
            print(f"Error analyzing codebase: {e}")
    
    def save_context(self, output_file: str) -> None:
        """Save the collected context to a file.
        
        Args:
            output_file: Path to save the context JSON
        """
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.context_data, f, indent=2)
            print(f"Context saved to {output_file}")
        except Exception as e:
            print(f"Error saving context: {e}")
    
    def load_context(self, input_file: str) -> None:
        """Load context from a file.
        
        Args:
            input_file: Path to the context JSON file
        """
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                self.context_data = json.load(f)
            print(f"Context loaded from {input_file}")
        except Exception as e:
            print(f"Error loading context: {e}")
    
    def get_codegen_prompt(self, task_type: str, additional_context: Dict[str, Any] = None) -> str:
        """Generate a Codegen prompt based on the collected context.
        
        Args:
            task_type: Type of task (e.g., "bug", "feature", "documentation")
            additional_context: Additional context to include
            
        Returns:
            Formatted prompt for Codegen
        """
        # Get repository info
        repo_info = f"""
        # Repository Information
        - Repository: {self.context_data["repository"]}
        - Owner: {self.context_data["metadata"].get("owner", "")}
        - Default Branch: {self.context_data["metadata"].get("default_branch", "")}
        - Languages: {", ".join(self.context_data["metadata"].get("languages", [])[:5])}
        """
        
        # Task-specific instructions
        task_instructions = {
            "bug": """
            ## Bug Fix Task
            
            Please analyze the issue and context information provided. Then:
            
            1. Identify the root cause of the bug
            2. Develop a fix for the issue
            3. Ensure any existing tests pass with your fix
            4. Create a PR with your changes
            5. Include a clear explanation of what was causing the bug and how your fix addresses it
            """,
            
            "feature": """
            ## Feature Implementation Task
            
            Please analyze the feature request and context information provided. Then:
            
            1. Design an implementation approach for the requested feature
            2. Implement the feature following project patterns and best practices
            3. Add appropriate tests for the new functionality
            4. Create a PR with your implementation
            5. Include documentation for how to use the new feature
            """,
            
            "documentation": """
            ## Documentation Task
            
            Please analyze the documentation needs and context information provided. Then:
            
            1. Identify the documentation gaps or issues
            2. Create or update documentation as needed
            3. Ensure the documentation is clear, concise, and well-structured
            4. Include examples where appropriate
            5. Create a PR with your documentation changes
            """,
            
            "code_review": """
            ## Code Review Task
            
            Please analyze the PR and context information provided. Then:
            
            1. Review the code changes for:
               - Bugs or issues
               - Performance concerns
               - Security vulnerabilities
               - Code quality and style
            2. Suggest improvements if needed
            3. Provide detailed feedback on the changes
            4. If the PR needs changes, create a new PR with your suggested fixes
            """,
            
            "refactoring": """
            ## Code Refactoring Task
            
            Please analyze the codebase and context information provided. Then:
            
            1. Identify code that could benefit from refactoring
            2. Implement refactoring changes to improve:
               - Code structure and organization
               - Readability and maintainability
               - Performance where applicable
            3. Ensure existing functionality is preserved (no behavior changes)
            4. Create a PR with your refactoring changes
            5. Include a clear explanation of your refactoring approach
            """
        }
        
        # Default task instructions if type not found
        if task_type not in task_instructions:
            task_instructions[task_type] = f"""
            ## {task_type.title()} Task
            
            Please analyze the context information provided and:
            
            1. Understand the requirements for this {task_type} task
            2. Implement an appropriate solution
            3. Add tests and documentation as needed
            4. Create a PR with your changes
            """
        
        # Context summary
        context_summary = """
        ## Context Information
        
        I've analyzed the repository and found relevant context:
        """
        
        # Add file snippets (limited to avoid huge prompts)
        files_summary = ""
        file_count = min(5, len(self.context_data["files"]))
        if file_count > 0:
            files_summary = "### Key Files:\n"
            for i, (file_path, file_info) in enumerate(list(self.context_data["files"].items())[:file_count]):
                # Get a preview of the file (first 20 lines)
                content_lines = file_info["content"].split("\n")[:20]
                preview = "\n".join(content_lines)
                files_summary += f"**{file_path}**:\n```\n{preview}\n...\n```\n\n"
        
        # Add issue information if available
        issues_summary = ""
        if self.context_data["issues"]:
            issues_summary = "### Related Issues:\n"
            for issue in self.context_data["issues"]:
                issues_summary += f"- #{issue.get('number', 'N/A')}: {issue.get('title', 'N/A')}\n"
        
        # Add PR information if available
        pr_summary = ""
        if self.context_data.get("pull_requests", []):
            pr_summary = "### Related Pull Requests:\n"
            for pr in self.context_data["pull_requests"]:
                pr_summary += f"- #{pr.get('number', 'N/A')}: {pr.get('title', 'N/A')}\n"
        
        # Add codebase analysis
        codebase_summary = ""
        if self.context_data["codebase"]:
            codebase_summary = "### Codebase Analysis:\n"
            if self.context_data["codebase"].get("entry_points", []):
                codebase_summary += f"Entry points: {', '.join(self.context_data['codebase']['entry_points'])}\n"
            if self.context_data["codebase"].get("config_files", []):
                codebase_summary += f"Config files: {', '.join(self.context_data['codebase']['config_files'])}\n"
        
        # Add additional context if provided
        additional_context_text = ""
        if additional_context:
            additional_context_text = "### Additional Context:\n"
            for key, value in additional_context.items():
                additional_context_text += f"**{key}**: {value}\n"
        
        # Final instructions
        final_instructions = """
        ## Final Instructions
        
        Please implement your solution as a pull request. Include any necessary tests and documentation.
        If you need additional information that's not provided in the context, please indicate what would be helpful.
        """
        
        # Combine all sections
        prompt = (
            repo_info + 
            task_instructions[task_type] + 
            context_summary + 
            files_summary + 
            issues_summary + 
            pr_summary + 
            codebase_summary + 
            additional_context_text + 
            final_instructions
        )
        
        return prompt
    
    def _run_command(self, command: str) -> str:
        """Run a shell command and return the output.
        
        Args:
            command: Shell command to run
            
        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")
            return ""
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in the system.
        
        Args:
            command: Command to check
            
        Returns:
            True if the command exists, False otherwise
        """
        try:
            subprocess.run(
                ["which", command], 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return True
        except subprocess.CalledProcessError:
            return False
def main():
    """Main function to run the context manager from CLI."""
    parser = argparse.ArgumentParser(description="Codegen Context Manager")
    
    # Command subparsers
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
    prompt_parser = subparsers.add_parser("prompt", help="Generate a Codegen prompt")
    prompt_parser.add_argument("--input", "-i", default="context.json", help="Input context file")
    prompt_parser.add_argument("--output", "-o", help="Output file (if not provided, print to stdout)")
    prompt_parser.add_argument("--task-type", "-t", default="feature", 
                               choices=["bug", "feature", "documentation", "code_review", "refactoring"],
                               help="Type of task")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create context manager
    context_manager = CodegenContext()
    
    # Process commands
    if args.command == "collect":
        # Collect context
        context_manager.collect_repo_metadata()
        
        if args.issue:
            context_manager.collect_issue_data(args.issue)
        
        if args.pr:
            context_manager.collect_pr_data(args.pr)
        
        context_manager.collect_code_context(
            file_patterns=args.file_patterns,
            max_files=args.max_files,
            exclude_patterns=args.exclude_patterns
        )
        
        context_manager.analyze_codebase()
        
        # Save context
        context_manager.save_context(args.output)
        
    elif args.command == "prompt":
        # Load context
        context_manager.load_context(args.input)
        
        # Generate prompt
        prompt = context_manager.get_codegen_prompt(args.task_type)
        
        # Output prompt
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"Prompt saved to {args.output}")
        else:
            print(prompt)
    
    else:
        parser.print_help()
if __name__ == "__main__":
    main()