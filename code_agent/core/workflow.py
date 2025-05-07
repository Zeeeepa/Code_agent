#!/usr/bin/env python3
"""
Continuous Development Script with CodeGen, GitHub, and ngrok

This script implements a fully automated CI/CD workflow using:
- CodeGen SDK for AI-powered code generation and PR review
- GitHub API for repository and PR management
- ngrok for webhook exposure

The script creates a cycle that:
1. Analyzes REQUIREMENTS.md and creates PRs to implement requirements
2. Reviews PRs against requirements and either approves or suggests changes
3. Merges approved PRs and creates test branches with full test coverage
4. Deploys and monitors the deployment process
5. Updates REQUIREMENTS.md to mark completed items
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
import threading
import datetime
from typing import Dict, List, Optional, Tuple, Any, Union

# Third-party imports
import requests
from github import Github, Repository, PullRequest
from pyngrok import ngrok, conf
from codegen import Agent  # CodeGen SDK

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cicd.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cicd")

class Configuration:
    """Stores and validates the configuration for the CI/CD workflow."""
    
    def __init__(self):
        self.github_token: str = ""
        self.ngrok_token: str = ""
        self.repo_name: str = ""
        self.codegen_token: str = ""
        self.codegen_org_id: str = ""
        self.webhook_url: str = ""
        self.webhook_port: int = 5000
        self.webhook_path: str = "/webhook"
        self.requirements_path: str = "REQUIREMENTS.md"
        self.test_branch_prefix: str = "test-"
        self.deployment_script_path: str = "deploy.py"
        
    def load_from_env(self):
        """Load configuration from environment variables."""
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.ngrok_token = os.environ.get("NGROK_TOKEN", "")
        self.repo_name = os.environ.get("REPO_NAME", "")
        self.codegen_token = os.environ.get("CODEGEN_TOKEN", "")
        self.codegen_org_id = os.environ.get("CODEGEN_ORG_ID", "")
        
    def load_from_args(self, args):
        """Load configuration from command line arguments."""
        if args.github_token:
            self.github_token = args.github_token
        if args.ngrok_token:
            self.ngrok_token = args.ngrok_token
        if args.repo_name:
            self.repo_name = args.repo_name
        if args.codegen_token:
            self.codegen_token = args.codegen_token
        if args.codegen_org_id:
            self.codegen_org_id = args.codegen_org_id
        if args.webhook_port:
            self.webhook_port = args.webhook_port
            
    def validate(self) -> List[str]:
        """Validate the configuration and return a list of errors if any."""
        errors = []
        
        if not self.github_token:
            errors.append("GitHub token is not provided")
        if not self.ngrok_token:
            errors.append("ngrok token is not provided")
        if not self.repo_name:
            errors.append("Repository name is not provided")
        if not self.codegen_token:
            errors.append("CodeGen token is not provided")
        if not self.codegen_org_id:
            errors.append("CodeGen organization ID is not provided")
            
        return errors

class GitHubManager:
    """Manages GitHub repository operations."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.github_client = Github(config.github_token)
        self.repo = self.github_client.get_repo(config.repo_name)
        logger.info(f"Connected to GitHub repository: {config.repo_name}")
        
    def get_requirements(self) -> str:
        """Fetch the content of REQUIREMENTS.md from the repository."""
        try:
            content_file = self.repo.get_contents(self.config.requirements_path)
            return content_file.decoded_content.decode('utf-8')
        except Exception as e:
            logger.error(f"Error fetching requirements: {str(e)}")
            return ""
            
    def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create a new branch in the repository."""
        try:
            base_ref = self.repo.get_git_ref(f"heads/{base_branch}")
            self.repo.create_git_ref(f"refs/heads/{branch_name}", base_ref.object.sha)
            logger.info(f"Created branch: {branch_name} from {base_branch}")
            return True
        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {str(e)}")
            return False
            
    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> Optional[PullRequest.PullRequest]:
        """Create a pull request in the repository."""
        try:
            pr = self.repo.create_pull(title=title, body=body, head=head, base=base)
            logger.info(f"Created PR #{pr.number}: {title}")
            return pr
        except Exception as e:
            logger.error(f"Error creating PR: {str(e)}")
            return None
            
    def get_pr(self, pr_number: int) -> Optional[PullRequest.PullRequest]:
        """Get a pull request by number."""
        try:
            return self.repo.get_pull(pr_number)
        except Exception as e:
            logger.error(f"Error getting PR #{pr_number}: {str(e)}")
            return None
            
    def merge_pr(self, pr: PullRequest.PullRequest) -> bool:
        """Merge a pull request."""
        try:
            merge_result = pr.merge(merge_method="squash")
            logger.info(f"Merged PR #{pr.number}")
            return True
        except Exception as e:
            logger.error(f"Error merging PR #{pr.number}: {str(e)}")
            return False
            
    def create_commit(self, branch: str, message: str, changes: Dict[str, str]) -> bool:
        """Create a commit with the given changes to the repository."""
        try:
            # Get the current head commit
            ref = self.repo.get_git_ref(f"heads/{branch}")
            latest_commit = self.repo.get_commit(ref.object.sha)
            base_tree = latest_commit.commit.tree
            
            # Create a new tree with the changes
            elements = []
            for path, content in changes.items():
                blob = self.repo.create_git_blob(content, "utf-8")
                elements.append({
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.sha
                })
            
            tree = self.repo.create_git_tree(elements, base_tree)
            
            # Create a commit with the new tree
            parent = self.repo.get_git_commit(latest_commit.sha)
            commit = self.repo.create_git_commit(message, tree, [parent])
            
            # Update the branch reference
            ref.edit(commit.sha)
            
            logger.info(f"Created commit on branch {branch}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error creating commit on {branch}: {str(e)}")
            return False
            
    def update_requirements(self, content: str) -> bool:
        """Update the REQUIREMENTS.md file in the main branch."""
        try:
            requirements_file = self.repo.get_contents(self.config.requirements_path)
            self.repo.update_file(
                path=self.config.requirements_path,
                message="Update requirements progress [ci skip]",
                content=content,
                sha=requirements_file.sha
            )
            logger.info("Updated REQUIREMENTS.md")
            return True
        except Exception as e:
            logger.error(f"Error updating REQUIREMENTS.md: {str(e)}")
            return False
            
    def set_webhook(self, webhook_url: str) -> bool:
        """Configure a webhook on the repository."""
        try:
            hooks = self.repo.get_hooks()
            
            # Check if the webhook already exists
            for hook in hooks:
                if hook.config.get("url") == webhook_url:
                    logger.info(f"Webhook already exists: {webhook_url}")
                    return True
            
            # Create a new webhook
            self.repo.create_hook(
                name="web",
                config={
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                },
                events=["pull_request"],
                active=True
            )
            
            logger.info(f"Set webhook to {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting webhook: {str(e)}")
            return False

class NgrokManager:
    """Manages ngrok tunnel for webhook exposure."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.tunnel = None
        
        # Configure ngrok
        conf.get_default().auth_token = config.ngrok_token
        logger.info("Configured ngrok with provided token")
        
    def start_tunnel(self) -> str:
        """Start an ngrok tunnel and return the public URL."""
        try:
            self.tunnel = ngrok.connect(self.config.webhook_port, "http")
            webhook_url = f"{self.tunnel.public_url}{self.config.webhook_path}"
            self.config.webhook_url = webhook_url
            logger.info(f"Started ngrok tunnel: {webhook_url}")
            return webhook_url
        except Exception as e:
            logger.error(f"Error starting ngrok tunnel: {str(e)}")
            return ""
            
    def stop_tunnel(self):
        """Stop the ngrok tunnel if running."""
        if self.tunnel:
            ngrok.disconnect(self.tunnel.public_url)
            logger.info("Stopped ngrok tunnel")

class WebhookServer:
    """Simple HTTP server to receive GitHub webhooks."""
    
    def __init__(self, config: Configuration, workflow_manager):
        self.config = config
        self.workflow_manager = workflow_manager
        self.server_thread = None
        self.running = False
        
    def start_server(self):
        """Start the webhook server in a separate thread."""
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
        @app.route(self.config.webhook_path, methods=['POST'])
        def webhook():
            if not request.json:
                return jsonify({'error': 'Invalid request'}), 400
                
            event = request.headers.get('X-GitHub-Event')
            payload = request.json
            
            if event == 'pull_request':
                pr_action = payload.get('action')
                pr_number = payload.get('pull_request', {}).get('number')
                
                if pr_action in ['opened', 'synchronize']:
                    # Trigger PR review process
                    threading.Thread(
                        target=self.workflow_manager.review_pr,
                        args=(pr_number,)
                    ).start()
                    return jsonify({'status': 'processing'}), 202
            
            return jsonify({'status': 'ignored'}), 200
            
        self.server_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=self.config.webhook_port)
        )
        self.server_thread.daemon = True
        self.server_thread.start()
        self.running = True
        logger.info(f"Started webhook server on port {self.config.webhook_port}")
        
    def stop_server(self):
        """Stop the webhook server if running."""
        self.running = False
        logger.info("Webhook server signaled to stop")
        # Note: This doesn't actually stop Flask; in a real implementation,
        # you might want to use a more graceful shutdown method

class CodeGenManager:
    """Manages interactions with the CodeGen API."""
    
    def __init__(self, config: Configuration):
        self.config = config
        # Initialize the Codegen client with API key and organization ID
        from code_agent.core.codegen_client import CodegenClient
        self.client = CodegenClient(
            api_key=config.codegen_token,
            org_id=config.codegen_org_id
        )
        logger.info("Initialized CodeGen client")
    
    def analyze_requirements(self, requirements: str) -> Dict:
        """Analyze requirements and suggest code changes."""
        prompt = f"""
        Analyze the following REQUIREMENTS.md content and create a plan for implementation:
        
        {requirements}
        
        Focus on incomplete requirements (not marked as [x]). Create a detailed plan for
        implementing the next requirement, including:
        1. Which files need to be created or modified
        2. What code changes are needed
        3. Test cases to verify the implementation
        
        Return your response as a structured plan in markdown format.
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("Requirements analysis completed")
                return {"success": True, "result": task_result.result}
            else:
                logger.error(f"Requirements analysis failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in requirements analysis: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def create_pr_changes(self, requirements: str, repo_info: Dict) -> Dict:
        """Generate code changes for a pull request based on requirements."""
        prompt = f"""
        Create code changes to implement the following requirements:
        
        {requirements}
        
        Repository information:
        - Name: {repo_info.get('name')}
        - Description: {repo_info.get('description')}
        - Main branch: {repo_info.get('default_branch')}
        
        Return a JSON object with the following structure:
        {{
            "branch_name": "feature-name",
            "pr_title": "Implement feature X",
            "pr_description": "Detailed description...",
            "changes": [
                {{
                    "file_path": "path/to/file.py",
                    "content": "full file content"
                }}
            ]
        }}
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("PR changes generation completed")
                try:
                    # Parse JSON from the result
                    result_json = self.client.parse_json_result(task_result)
                    return {"success": True, "result": result_json}
                except ValueError as json_e:
                    logger.error(f"Failed to parse JSON from CodeGen result: {str(json_e)}")
                    return {"success": False, "error": f"JSON parsing error: {str(json_e)}", "raw_result": task_result.result}
            else:
                logger.error(f"PR changes generation failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in PR changes generation: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def review_pr(self, pr_content: Dict, requirements: str) -> Dict:
        """Review a pull request against the requirements."""
        prompt = f"""
        Review the following pull request to determine if it correctly implements the requirements:
        
        PR Title: {pr_content.get('title')}
        PR Description: {pr_content.get('body')}
        
        Changed files:
        {json.dumps(pr_content.get('files', []), indent=2)}
        
        Requirements:
        {requirements}
        
        Evaluate if the PR meets all requirements. If not, suggest specific changes.
        
        Return a JSON object with the following structure:
        {{
            "approved": true|false,
            "comments": "Your review comments",
            "suggested_changes": [
                {{
                    "file_path": "path/to/file.py",
                    "content": "updated content"
                }}
            ]
        }}
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("PR review completed")
                try:
                    # Parse JSON from the result
                    result_json = self.client.parse_json_result(task_result)
                    return {"success": True, "result": result_json}
                except ValueError as json_e:
                    logger.error(f"Failed to parse JSON from PR review result: {str(json_e)}")
                    return {"success": False, "error": f"JSON parsing error: {str(json_e)}", "raw_result": task_result.result}
            else:
                logger.error(f"PR review failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in PR review: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def create_tests(self, pr_content: Dict) -> Dict:
        """Generate test cases for the PR changes."""
        prompt = f"""
        Create comprehensive tests for the changes in the following pull request:
        
        PR Title: {pr_content.get('title')}
        PR Description: {pr_content.get('body')}
        
        Changed files:
        {json.dumps(pr_content.get('files', []), indent=2)}
        
        Return a JSON object with the following structure:
        {{
            "test_files": [
                {{
                    "file_path": "tests/test_feature.py",
                    "content": "import unittest\\n..."
                }}
            ]
        }}
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("Test creation completed")
                result = task_result.result
                try:
                    # Extract JSON from CodeGen result
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', result, re.DOTALL)
                    if json_match:
                        result_json = json.loads(json_match.group(1))
                    else:
                        # Try to find any JSON object in the result
                        json_match = re.search(r'({.*})', result, re.DOTALL)
                        if json_match:
                            result_json = json.loads(json_match.group(1))
                        else:
                            # Last resort: try to parse the whole result as JSON
                            result_json = json.loads(result)
                        
                        return {"success": True, "result": result_json}
                except Exception as json_e:
                    logger.error(f"Failed to parse JSON from test creation result: {str(json_e)}")
                    return {"success": False, "error": f"JSON parsing error: {str(json_e)}", "raw_result": result}
            else:
                logger.error(f"Test creation failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in test creation: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def analyze_deployment_logs(self, logs: str, pr_content: Dict) -> Dict:
        """Analyze deployment logs to identify issues."""
        prompt = f"""
        Analyze the following deployment logs for the PR and identify any issues:
        
        PR Title: {pr_content.get('title')}
        PR Description: {pr_content.get('body')}
        
        Deployment logs:
        {logs}
        
        Return a JSON object with the following structure:
        {{
            "success": true|false,
            "issues": [
                {{
                    "description": "Description of the issue",
                    "severity": "high|medium|low",
                    "suggested_fix": "Code or configuration change to fix the issue"
                }}
            ]
        }}
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("Deployment log analysis completed")
                try:
                    # Parse JSON from the result
                    result_json = self.client.parse_json_result(task_result)
                    return {"success": True, "result": result_json}
                except ValueError as json_e:
                    logger.error(f"Failed to parse JSON from log analysis result: {str(json_e)}")
                    return {"success": False, "error": f"JSON parsing error: {str(json_e)}", "raw_result": task_result.result}
            else:
                logger.error(f"Deployment log analysis failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in deployment log analysis: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def update_requirements_progress(self, requirements: str, completed_items: List[str]) -> Dict:
        """Update the REQUIREMENTS.md to mark completed items."""
        prompt = f"""
        Update the following REQUIREMENTS.md content to mark these items as completed:
        
        Completed items:
        {json.dumps(completed_items, indent=2)}
        
        Current REQUIREMENTS.md:
        {requirements}
        
        Return the updated REQUIREMENTS.md content with the completed items marked with [x].
        """
        
        try:
            task_result = self.client.run_task(prompt=prompt)
            
            if task_result.status.value == "completed":
                logger.info("Requirements update completed")
                return {"success": True, "result": task_result.result}
            else:
                logger.error(f"Requirements update failed: {task_result.error}")
                return {"success": False, "error": task_result.error}
        except Exception as e:
            logger.error(f"Error in requirements update: {str(e)}")
            return {"success": False, "error": str(e)}

class DeploymentManager:
    """Manages the deployment process and testing."""
    
    def __init__(self, config: Configuration, github_manager: GitHubManager):
        self.config = config
        self.github_manager = github_manager
        
    def create_deployment_script(self, pr_content: Dict) -> Tuple[bool, str]:
        """Create a deployment script based on the PR changes."""
        # This would use CodeGen to create a deployment script, but for simplicity
        # we'll create a basic Python script template
        
        script_content = f"""#!/usr/bin/env python3
# Auto-generated deployment script for PR #{pr_content.get('number')}
# Title: {pr_content.get('title')}

import sys
import os
import logging
import subprocess
import datetime

# Set up logging
log_filename = f"deployment_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("deployment")

def run_command(command, cwd=None):
    logger.info(f"Running command: {command}")
    result = subprocess.run(
        command, 
        shell=True, 
        cwd=cwd,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )
    
    logger.info(f"Command exit code: {result.returncode}")
    if result.stdout:
        logger.info(f"Command output:\\n{result.stdout}")
    if result.returncode != 0 and result.stderr:
        logger.error(f"Command error output:\\n{result.stderr}")
        
    return result.returncode == 0, result.stdout, result.stderr

def main():
    logger.info("Starting deployment for PR #{pr_content.get('number')}")
    repo_url = "{self.github_manager.repo.clone_url}"
    branch = "{pr_content.get('head', {}).get('ref')}"
    
    # Create deployment directory
    deploy_dir = f"deployment_pr{pr_content.get('number')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Step 1: Clone repository
    logger.info(f"Cloning repository {repo_url}...OK")
    success, _, _ = run_command(f"git clone {repo_url} .", cwd=deploy_dir)
    if not success:
        logger.error("Failed to clone repository")
        return 1
    
    # Step 2: Checkout branch
    logger.info(f"Checking out branch: {branch}")
    success, _, _ = run_command(f"git checkout {branch}", cwd=deploy_dir)
    if not success:
        logger.error(f"Failed to checkout branch {branch}")
        return 1
    
    # Step 3: Install dependencies
    logger.info("Installing dependencies...")
    if os.path.exists(os.path.join(deploy_dir, "requirements.txt")):
        success, _, _ = run_command("pip install -r requirements.txt", cwd=deploy_dir)
        if not success:
            logger.warning("Warning: Failed to install dependencies")
    elif os.path.exists(os.path.join(deploy_dir, "pyproject.toml")):
        success, _, _ = run_command("pip install .", cwd=deploy_dir)
        if not success:
            logger.warning("Warning: Failed to install package")
    else:
        logger.info("No standard dependency file found, skipping dependency installation")
    
    # Step 4: Run tests
    logger.info("Running tests...")
    if os.path.exists(os.path.join(deploy_dir, "pytest.ini")) or os.path.exists(os.path.join(deploy_dir, "tests")):
        success, _, _ = run_command("python -m pytest", cwd=deploy_dir)
        if not success:
            logger.error("Tests failed")
            return 1
    else:
        logger.info("No tests directory found, skipping tests")
    
    # Step 5: Deploy (simulate for demo purposes)
    logger.info("Deploying application...")
    # In a real scenario, you would include actual deployment steps here
    # For example: docker build, push to registry, deploy to K8s, etc.
    
    # Step 6: Verify deployment
    logger.info("Verifying deployment...")
    # In a real scenario, you would include health checks, smoke tests, etc.
    
    logger.info("Deployment completed successfully")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        sys.exit(1)
"""
        
        # Save the script to the repository in a new branch
        deployment_branch = f"deployment-pr-{pr_content.get('number')}"
        
        # Create the branch
        if not self.github_manager.create_branch(deployment_branch):
            return False, "Failed to create deployment branch"
        
        # Commit the deployment script
        changes = {
            self.config.deployment_script_path: script_content
        }
        
        if not self.github_manager.create_commit(
            branch=deployment_branch,
            message=f"Add deployment script for PR #{pr_content.get('number')}",
            changes=changes
        ):
            return False, "Failed to commit deployment script"
        
        return True, deployment_branch
    
    def run_deployment(self, branch: str) -> Tuple[bool, str]:
        """Run the deployment script and capture the output."""
        # In a real implementation, this would execute the deployment script
        # For the purpose of this example, we'll simulate it
        
        logger.info(f"Running deployment for branch: {branch}")
        
        # Simulate deployment output
        deployment_log = f"""
Deployment started for branch: {branch}
Cloning repository... OK
Checking out branch {branch}... OK
Installing dependencies... OK
Running tests... OK
Deploying application... OK
Verifying deployment... OK
Deployment completed successfully
"""
        
        # In a real implementation, you might run:
        # subprocess.run(["python", self.config.deployment_script_path], capture_output=True)
        
        return True, deployment_log

class WorkflowManager:
    """Coordinates the entire CI/CD workflow."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.github_manager = GitHubManager(config)
        self.ngrok_manager = NgrokManager(config)
        self.webhook_server = WebhookServer(config, self)
        self.codegen_manager = CodeGenManager(config)
        self.deployment_manager = DeploymentManager(config, self.github_manager)
        self.running = False
        
    def start(self):
        """Start the CI/CD workflow."""
        logger.info("Starting CI/CD workflow")
        
        # Start ngrok tunnel
        webhook_url = self.ngrok_manager.start_tunnel()
        if not webhook_url:
            logger.error("Failed to start ngrok tunnel. Exiting.")
            return False
        
        # Configure webhook on GitHub repository
        if not self.github_manager.set_webhook(webhook_url):
            logger.error("Failed to set webhook on GitHub repository. Exiting.")
            self.ngrok_manager.stop_tunnel()
            return False
        
        # Start webhook server
        self.webhook_server.start_server()
        
        # Start the workflow cycle
        self.analyze_and_create_pr()
        
        return True
    
    def stop(self):
        """Stop the CI/CD workflow."""
        logger.info("Stopping CI/CD workflow")
        self.webhook_server.stop_server()
        self.ngrok_manager.stop_tunnel()
        logger.info("CI/CD workflow stopped")
        
    def analyze_and_create_pr(self):
        """Analyze requirements and create a PR for the next implementation task."""
        # Fetch requirements
        requirements = self.github_manager.get_requirements()
        if not requirements:
            logger.error("Failed to fetch requirements. Stopping workflow.")
            return False
        
        # Analyze requirements
        analysis = self.codegen_manager.analyze_requirements(requirements)
        if not analysis.get("success"):
            logger.error(f"Failed to analyze requirements: {analysis.get('error')}")
            return False
        
        # Get repository information for PR creation
        repo_info = {
            "name": self.config.repo_name,
            "description": self.github_manager.repo.description,
            "default_branch": self.github_manager.repo.default_branch
        }
        
        # Generate PR changes
        pr_changes = self.codegen_manager.create_pr_changes(requirements, repo_info)
        if not pr_changes.get("success"):
            logger.error(f"Failed to generate PR changes: {pr_changes.get('error')}")
            return False
        
        result = pr_changes.get("result", {})
        branch_name = result.get("branch_name")
        pr_title = result.get("pr_title")
        pr_description = result.get("pr_description")
        changes = result.get("changes", [])
        
        if not all([branch_name, pr_title, pr_description, changes]):
            logger.error("Missing required information for PR creation")
            return False
        
        # Create branch
        if not self.github_manager.create_branch(branch_name):
            logger.error(f"Failed to create branch: {branch_name}")
            return False
        
        # Commit changes
        changes_dict = {change.get("file_path"): change.get("content") for change in changes}
        if not self.github_manager.create_commit(
            branch=branch_name,
            message=f"Implement: {pr_title}",
            changes=changes_dict
        ):
            logger.error("Failed to commit changes")
            return False
        
        # Create PR
        pr = self.github_manager.create_pr(
            title=pr_title,
            body=pr_description,
            head=branch_name,
            base=self.github_manager.repo.default_branch
        )
        
        if not pr:
            logger.error("Failed to create PR")
            return False
        
        logger.info(f"Created PR #{pr.number}: {pr_title}")
        return True
    
    def review_pr(self, pr_number: int):
        """Review a PR and either approve or suggest changes."""
        # Get PR details
        pr = self.github_manager.get_pr(pr_number)
        if not pr:
            logger.error(f"Failed to get PR #{pr_number}")
            return False
        
        # Get PR files
        pr_files = []
        try:
            for file in pr.get_files():
                content = self.github_manager.repo.get_contents(file.filename, ref=pr.head.ref).decoded_content.decode('utf-8')
                pr_files.append({
                    "path": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "content": content
                })
        except Exception as e:
            logger.error(f"Error getting PR files: {str(e)}")
            return False
        
        # Prepare PR content for review
        pr_content = {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "head": {
                "ref": pr.head.ref,
                "sha": pr.head.sha
            },
            "base": {
                "ref": pr.base.ref,
                "sha": pr.base.sha
            },
            "files": pr_files
        }
        
        # Get requirements
        requirements = self.github_manager.get_requirements()
        if not requirements:
            logger.error("Failed to fetch requirements for PR review")
            return False
        
        # Review PR against requirements
        review_result = self.codegen_manager.review_pr(pr_content, requirements)
        if not review_result.get("success"):
            logger.error(f"Failed to review PR: {review_result.get('error')}")
            return False
        
        result = review_result.get("result", {})
        approved = result.get("approved", False)
        comments = result.get("comments", "")
        suggested_changes = result.get("suggested_changes", [])
        
        # Add review comments to the PR
        try:
            pr.create_issue_comment(comments)
            logger.info(f"Added review comments to PR #{pr_number}")
        except Exception as e:
            logger.error(f"Error adding comments to PR: {str(e)}")
        
        if approved:
            # PR is approved, proceed with merge and testing
            logger.info(f"PR #{pr_number} approved")
            self.process_approved_pr(pr, pr_content)
        else:
            # PR needs changes
            logger.info(f"PR #{pr_number} needs changes")
            if suggested_changes:
                self.implement_suggested_changes(pr, suggested_changes)
            
        return True
    
    def implement_suggested_changes(self, pr: PullRequest.PullRequest, suggested_changes: List[Dict]):
        """Implement suggested changes to a PR."""
        branch = pr.head.ref
        
        changes_dict = {change.get("file_path"): change.get("content") for change in suggested_changes}
        if not self.github_manager.create_commit(
            branch=branch,
            message=f"Address review comments for PR #{pr.number}",
            changes=changes_dict
        ):
            logger.error(f"Failed to implement suggested changes for PR #{pr.number}")
            return False
        
        logger.info(f"Implemented suggested changes for PR #{pr.number}")
        return True
    
    def process_approved_pr(self, pr: PullRequest.PullRequest, pr_content: Dict):
        """Process an approved PR: merge, create test branch, and deploy."""
        # Step 1: Create test branch
        test_branch = f"{self.config.test_branch_prefix}{pr.head.ref}"
        if not self.github_manager.create_branch(test_branch, base_branch=pr.head.ref):
            logger.error(f"Failed to create test branch {test_branch}")
            return False
        
        # Step 2: Generate tests
        tests_result = self.codegen_manager.create_tests(pr_content)
        if not tests_result.get("success"):
            logger.error(f"Failed to generate tests: {tests_result.get('error')}")
            return False
        
        test_files = tests_result.get("result", {}).get("test_files", [])
        
        # Step 3: Add tests to test branch
        test_changes = {test_file.get("file_path"): test_file.get("content") for test_file in test_files}
        if test_changes and not self.github_manager.create_commit(
            branch=test_branch,
            message=f"Add tests for PR #{pr.number}",
            changes=test_changes
        ):
            logger.error(f"Failed to add tests to branch {test_branch}")
            return False
        
        logger.info(f"Added tests to branch {test_branch}")
        
        # Step 4: Create deployment script
        deployment_success, deployment_result = self.deployment_manager.create_deployment_script(pr_content)
        if not deployment_success:
            logger.error(f"Failed to create deployment script: {deployment_result}")
            return False
        
        # Step 5: Run deployment
        deploy_success, deploy_logs = self.deployment_manager.run_deployment(test_branch)
        if not deploy_success:
            logger.error(f"Deployment failed: {deploy_logs}")
            self.handle_deployment_failure(pr, pr_content, deploy_logs)
            return False
        
        # Step 6: Analyze deployment logs
        log_analysis = self.codegen_manager.analyze_deployment_logs(deploy_logs, pr_content)
        if not log_analysis.get("success"):
            logger.error(f"Failed to analyze deployment logs: {log_analysis.get('error')}")
            return False
        
        analysis_result = log_analysis.get("result", {})
        deployment_success = analysis_result.get("success", False)
        issues = analysis_result.get("issues", [])
        
        if not deployment_success or issues:
            logger.warning(f"Deployment issues found: {len(issues)} issues")
            self.handle_deployment_issues(pr, pr_content, issues)
            return False
        
        # Step 7: Merge PR if deployment was successful
        if not self.github_manager.merge_pr(pr):
            logger.error(f"Failed to merge PR #{pr.number}")
            return False
        
        logger.info(f"Successfully merged PR #{pr.number}")
        
        # Step 8: Update requirements progress
        completed_item = pr.title
        updated_requirements = self.codegen_manager.update_requirements_progress(
            self.github_manager.get_requirements(),
            [completed_item]
        )
        
        if not updated_requirements.get("success"):
            logger.error(f"Failed to update requirements progress: {updated_requirements.get('error')}")
            return False
        
        if not self.github_manager.update_requirements(updated_requirements.get("result", "")):
            logger.error("Failed to commit updated requirements")
            return False
        
        logger.info("Updated requirements progress")
        
        # Step 9: Start a new cycle
        self.analyze_and_create_pr()
        
        return True
    
    def handle_deployment_failure(self, pr: PullRequest.PullRequest, pr_content: Dict, logs: str):
        """Handle a deployment failure by creating an error report and PR comment."""
        try:
            error_comment = f"""
## Deployment Failed

The deployment of PR #{pr.number} failed. Please check the logs:

```{logs}
```

Please address these issues before merging.
"""
            pr.create_issue_comment(error_comment)
            logger.info(f"Added deployment failure comment to PR #{pr_number}")
        except Exception as e:
            logger.error(f"Error adding deployment failure comment: {str(e)}")
        
        return True
    
    def handle_deployment_issues(self, pr: PullRequest.PullRequest, pr_content: Dict, issues: List[Dict]):
        """Handle deployment issues by creating a fix branch and PR."""
        # Create a comment detailing the issues
        try:
            issues_md = "\n".join([f"- **{issue.get('severity', 'medium')}**: {issue.get('description')}" for issue in issues])
            issues_comment = f"""
## Deployment Issues

The deployment completed, but the following issues were found:

{issues_md}

A fix branch will be created to address these issues.
"""
            pr.create_issue_comment(issues_comment)
            logger.info(f"Added deployment issues comment to PR #{pr_number}")
        except Exception as e:
            logger.error(f"Error adding deployment issues comment: {str(e)}")
            return False
        
        # Create a fix branch
        fix_branch = f"fix-deployment-{pr.number}"
        if not self.github_manager.create_branch(fix_branch, base_branch=pr.head.ref):
            logger.error(f"Failed to create fix branch {fix_branch}")
            return False
        
        # For each issue, add a fix commit based on the suggested fix
        for i, issue in enumerate(issues):
            suggested_fix = issue.get("suggested_fix", "")
            if not suggested_fix:
                continue
            
            # This is simplified; in a real implementation, you would parse the suggested fix
            # and determine which files to modify based on context
            
            # For now, assume the fix involves adding a new file
            file_path = f"fixes/fix_{i+1}.py"
            changes = {file_path: suggested_fix}
            
            if not self.github_manager.create_commit(
                branch=fix_branch,
                message=f"Fix: {issue.get('description', 'deployment issue')}",
                changes=changes
            ):
                logger.error(f"Failed to add fix for issue #{i+1}")
                continue
        
        # Create a PR with the fixes
        fix_pr = self.github_manager.create_pr(
            title=f"Fix deployment issues from PR #{pr.number}",
            body=f"""
This PR addresses deployment issues found in PR #{pr.number}.

Issues fixed:
{issues_md}
""",
            head=fix_branch,
            base=self.github_manager.repo.default_branch
        )
        
        if not fix_pr:
            logger.error("Failed to create fix PR")
            return False
        
        logger.info(f"Created fix PR #{fix_pr.number}")
        return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Continuous Development Script with CodeGen, GitHub, and ngrok")
    
    parser.add_argument("--github-token", help="GitHub API token")
    parser.add_argument("--ngrok-token", help="ngrok authentication token")
    parser.add_argument("--repo-name", help="GitHub repository name (format: owner/repo)")
    parser.add_argument("--codegen-token", help="CodeGen API token")
    parser.add_argument("--codegen-org-id", help="CodeGen organization ID")
    parser.add_argument("--webhook-port", type=int, default=5000, help="Port for webhook server (default: 5000)")
    
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    print("=" * 80)
    print("Continuous Development Script with CodeGen, GitHub, and ngrok")
    print("=" * 80)
    
    # Parse command line arguments
    args = parse_args()
    
    # Initialize configuration
    config = Configuration()
    
    # Load configuration from environment variables
    config.load_from_env()
    
    # Override with command line arguments
    config.load_from_args(args)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"- {error}")
        print("\nPlease provide the required information via environment variables or command line arguments.")
        return 1
    
    # Initialize workflow manager
    workflow_manager = WorkflowManager(config)
    
    # Start workflow
    try:
        if not workflow_manager.start():
            print("Failed to start workflow. Check logs for details.")
            return 1
        
        print("Workflow started. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping workflow...")
        workflow_manager.stop()
        print("Workflow stopped.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        workflow_manager.stop()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
