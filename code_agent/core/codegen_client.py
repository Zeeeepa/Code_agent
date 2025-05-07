#!/usr/bin/env python3
"""
Codegen API Client

This module provides a robust client for interacting with the Codegen API.
It handles authentication, request/response formatting, error handling,
and provides a higher-level abstraction over the Codegen API.
"""

import os
import time
import json
import logging
import re
import random
import requests
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from codegen import Agent
except ImportError:
    Agent = None

# Set up logging
logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    """Enum representing possible task statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

class ReviewType(str, Enum):
    """Enum representing different types of code reviews."""
    STANDARD = "standard"
    GEMINI = "gemini"
    KORBIT = "korbit"
    IMPROVE = "improve"

@dataclass
class TaskResult:
    """Represents the result of a Codegen task."""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

class CircuitBreakerState(Enum):
    """Enum representing the states of the circuit breaker."""
    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"      # Failure threshold exceeded, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service is back to normal

class CircuitBreaker:
    """
    Implements the circuit breaker pattern to prevent repeated calls to a failing service.
    
    This helps avoid overwhelming a service that is already struggling and gives it time to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "codegen-api"
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening the circuit
            recovery_timeout: Time in seconds to wait before trying to recover (half-open state)
            name: Name of this circuit breaker for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        
    def allow_request(self) -> bool:
        """
        Check if a request should be allowed based on the current circuit state.
        
        Returns:
            True if the request should be allowed, False otherwise
        """
        now = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
            
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if now - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit {self.name} transitioning from OPEN to HALF_OPEN")
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
            
        if self.state == CircuitBreakerState.HALF_OPEN:
            # In half-open state, allow only one request to test the service
            return True
            
        return False
        
    def record_success(self) -> None:
        """Record a successful request and reset the circuit if needed."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info(f"Circuit {self.name} recovered, transitioning to CLOSED")
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            
    def record_failure(self) -> None:
        """Record a failed request and potentially open the circuit."""
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning(f"Circuit {self.name} failed in HALF_OPEN state, returning to OPEN")
            self.state = CircuitBreakerState.OPEN
            return
            
        self.failure_count += 1
        if self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit {self.name} threshold reached ({self.failure_count} failures), transitioning to OPEN")
            self.state = CircuitBreakerState.OPEN

class CodegenClient:
    """
    A client for interacting with the Codegen API.
    
    This client provides a higher-level abstraction over the Codegen API,
    handling authentication, request/response formatting, error handling,
    and polling for task completion.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        org_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        polling_interval: float = 10.0,
        polling_timeout: float = 300.0,
        request_timeout: float = 30.0,
        auto_install: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_recovery_time: float = 60.0
    ):
        """
        Initialize the Codegen client.
        
        Args:
            api_key: Codegen API key. If not provided, will try to get from CODEGEN_TOKEN env var.
            org_id: Codegen organization ID. If not provided, will try to get from CODEGEN_ORG_ID env var.
            max_retries: Maximum number of retries for API calls.
            retry_delay: Initial delay between retries (will be exponentially increased).
            polling_interval: Interval in seconds between polling for task status.
            polling_timeout: Maximum time in seconds to wait for a task to complete.
            request_timeout: Timeout in seconds for individual API requests.
            auto_install: Whether to automatically install the Codegen SDK if not found.
            circuit_breaker_threshold: Number of consecutive failures before opening the circuit.
            circuit_breaker_recovery_time: Time in seconds to wait before trying to recover.
        """
        # Load configuration from environment variables if not provided
        self.api_key = api_key or os.environ.get("CODEGEN_TOKEN") or os.environ.get("CODEGEN_API_KEY")
        self.org_id = org_id or os.environ.get("CODEGEN_ORG_ID") or os.environ.get("CODEGEN_ORGANIZATION_ID")
        self.max_retries = int(os.environ.get("CODEGEN_MAX_RETRIES", max_retries))
        self.retry_delay = float(os.environ.get("CODEGEN_RETRY_DELAY", retry_delay))
        self.polling_interval = float(os.environ.get("CODEGEN_POLLING_INTERVAL", polling_interval))
        self.polling_timeout = float(os.environ.get("CODEGEN_POLLING_TIMEOUT", polling_timeout))
        self.request_timeout = float(os.environ.get("CODEGEN_REQUEST_TIMEOUT", request_timeout))
        
        if not self.api_key:
            raise ValueError("Codegen API key is required. Provide it as an argument or set the CODEGEN_TOKEN or CODEGEN_API_KEY environment variable.")
        
        if not self.org_id:
            raise ValueError("Codegen organization ID is required. Provide it as an argument or set the CODEGEN_ORG_ID or CODEGEN_ORGANIZATION_ID environment variable.")
        
        # Initialize the circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.environ.get("CODEGEN_CIRCUIT_BREAKER_THRESHOLD", circuit_breaker_threshold)),
            recovery_timeout=float(os.environ.get("CODEGEN_CIRCUIT_BREAKER_RECOVERY_TIME", circuit_breaker_recovery_time))
        )
        
        # Initialize the Codegen Agent
        global Agent
        if Agent is None and auto_install:
            logger.info("Codegen SDK not found. Installing...")
            try:
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "codegen"])
                from codegen import Agent
            except (subprocess.SubprocessError, ImportError) as e:
                logger.error(f"Failed to auto-install Codegen SDK: {e}")
                raise ImportError(f"Failed to auto-install Codegen SDK: {e}. Please install it manually with 'pip install codegen'.")
        
        if Agent is None:
            raise ImportError("Failed to import Codegen SDK. Please install it manually with 'pip install codegen'.")
        
        self.agent = Agent(api_key=self.api_key, org_id=self.org_id)
        logger.info(f"Initialized Codegen client with org_id={self.org_id[:4]}***")
    
    def _validate_prompt(self, prompt: str) -> None:
        """
        Validate the prompt before sending it to the API.
        
        Args:
            prompt: The prompt to validate
            
        Raises:
            ValueError: If the prompt is invalid
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        
        if len(prompt) > 32000:  # Assuming a reasonable token limit
            raise ValueError(f"Prompt is too long ({len(prompt)} characters). Maximum allowed is 32000 characters.")
    
    def _calculate_retry_delay(self, attempt: int, jitter: bool = True) -> float:
        """
        Calculate the delay before the next retry attempt with exponential backoff.
        
        Args:
            attempt: The current attempt number (0-based)
            jitter: Whether to add random jitter to avoid thundering herd problem
            
        Returns:
            The delay in seconds before the next retry
        """
        delay = self.retry_delay * (2 ** attempt)
        
        # Add jitter (random variation) to avoid all clients retrying at the same time
        if jitter:
            delay = delay * (0.5 + random.random())
            
        return delay
    
    def run_task(
        self, 
        prompt: str, 
        wait_for_completion: bool = True,
        callback: Optional[Callable[[TaskResult], None]] = None
    ) -> TaskResult:
        """
        Run a task with the Codegen API.
        
        Args:
            prompt: The prompt to send to the Codegen API.
            wait_for_completion: Whether to wait for the task to complete.
            callback: Optional callback function to call with task updates.
            
        Returns:
            A TaskResult object containing the task status and result.
        """
        logger.info("Starting Codegen task")
        
        # Validate the prompt
        try:
            self._validate_prompt(prompt)
        except ValueError as e:
            logger.error(f"Invalid prompt: {e}")
            return TaskResult(
                task_id="",
                status=TaskStatus.FAILED,
                error=str(e)
            )
        
        # Check if the circuit breaker allows the request
        if not self.circuit_breaker.allow_request():
            logger.error("Circuit breaker is open, request blocked")
            return TaskResult(
                task_id="",
                status=TaskStatus.FAILED,
                error="Service is currently unavailable due to repeated failures. Please try again later."
            )
        
        # Run the task with retries
        task = None
        for attempt in range(self.max_retries):
            try:
                task = self.agent.run(prompt=prompt)
                # Record success in the circuit breaker
                self.circuit_breaker.record_success()
                break
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(f"Error running Codegen task (attempt {attempt+1}/{self.max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to run Codegen task after {self.max_retries} attempts: {e}")
                    # Record failure in the circuit breaker
                    self.circuit_breaker.record_failure()
                    return TaskResult(
                        task_id="",
                        status=TaskStatus.FAILED,
                        error=str(e)
                    )
        
        if task is None:
            # Record failure in the circuit breaker
            self.circuit_breaker.record_failure()
            return TaskResult(
                task_id="",
                status=TaskStatus.FAILED,
                error="Failed to create task"
            )
        
        task_id = getattr(task, 'id', str(task))
        logger.info(f"Task created with ID: {task_id}")
        
        # Create initial task result
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING
        )
        
        # If not waiting for completion, return immediately
        if not wait_for_completion:
            if callback:
                callback(result)
            return result
        
        # Poll for task completion
        start_time = time.time()
        while time.time() - start_time < self.polling_timeout:
            try:
                task.refresh()
                
                # Update status
                status_str = getattr(task, 'status', 'unknown')
                try:
                    result.status = TaskStatus(status_str.lower())
                except ValueError:
                    result.status = TaskStatus.UNKNOWN
                
                # Call callback if provided
                if callback:
                    callback(result)
                
                # Check if task is complete
                if result.status == TaskStatus.COMPLETED:
                    result.result = getattr(task, 'result', None)
                    logger.info("Task completed successfully")
                    return result
                elif result.status == TaskStatus.FAILED:
                    result.error = getattr(task, 'error', 'Unknown error')
                    logger.error(f"Task failed: {result.error}")
                    return result
                
                # Log status and wait
                logger.info(f"Task status: {result.status}. Waiting...")
                time.sleep(self.polling_interval)
            except Exception as e:
                logger.warning(f"Error checking task status: {e}")
                time.sleep(self.polling_interval)
        
        # Timeout
        logger.error(f"Task timed out after {self.polling_timeout} seconds")
        result.status = TaskStatus.FAILED
        result.error = f"Task timed out after {self.polling_timeout} seconds"
        return result
    
    def parse_json_result(self, result: TaskResult) -> Dict[str, Any]:
        """
        Parse JSON from a task result.
        
        This handles various formats that the Codegen API might return,
        including JSON embedded in markdown code blocks.
        
        Args:
            result: The TaskResult to parse.
            
        Returns:
            The parsed JSON as a dictionary.
        """
        if not result.result:
            raise ValueError("Task result is empty")
        
        # Store the raw result for debugging
        raw_result = result.result
        
        # Filter out lines starting with '#'
        filtered_result = '\n'.join([line for line in raw_result.split('\n') if not line.strip().startswith('#')])
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n\s*```', filtered_result, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from code block: {e}")
        
        # Try to find any JSON object in the result
        json_match = re.search(r'({.*})', filtered_result, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from matched object: {e}")
        
        # Last resort: try to parse the whole result as JSON
        try:
            return json.loads(filtered_result)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from result: {e}")
            # Include more context in the error message for better debugging
            preview = filtered_result[:500] + ('...' if len(filtered_result) > 500 else '')
            raise ValueError(f"Failed to parse JSON from result: {e}. Preview: {preview}")
    
    def parse_review_command(self, command: str) -> Tuple[ReviewType, Dict[str, Any]]:
        """
        Parse a review command to determine the review type and options.
        
        Args:
            command: The review command (e.g., "/review", "/gemini-review", "/korbit-review", "/improve")
            
        Returns:
            A tuple of (ReviewType, options_dict)
        """
        command = command.strip().lower()
        options = {}
        
        if command.startswith("/gemini"):
            return ReviewType.GEMINI, options
        elif command.startswith("/korbit"):
            return ReviewType.KORBIT, options
        elif command.startswith("/improve"):
            return ReviewType.IMPROVE, options
        else:
            return ReviewType.STANDARD, options
    
    def generate_review_prompt(self, 
                              review_type: ReviewType, 
                              pr_data: Dict[str, Any],
                              options: Dict[str, Any] = None) -> str:
        """
        Generate a prompt for a code review based on the review type.
        
        Args:
            review_type: The type of review to generate
            pr_data: Data about the pull request to review
            options: Additional options for the review
            
        Returns:
            A prompt string for the Codegen API
        """
        options = options or {}
        
        # Extract PR details
        pr_title = pr_data.get("title", "")
        pr_description = pr_data.get("body", "")
        pr_diff = pr_data.get("diff", "")
        
        # Base prompt for all review types
        base_prompt = f"""
        Please review the following pull request:
        
        Title: {pr_title}
        
        Description:
        {pr_description}
        
        Changes:
        {pr_diff}
        """
        
        # Add specific instructions based on review type
        if review_type == ReviewType.GEMINI:
            return base_prompt + """
            Perform a thorough code review focusing on:
            1. Code correctness and potential bugs
            2. Performance issues
            3. Security vulnerabilities
            4. Code style and best practices
            5. Architecture and design patterns
            
            Format your review as a list of comments, with each comment on a separate line.
            Lines starting with '#' will be ignored.
            """
        elif review_type == ReviewType.KORBIT:
            return base_prompt + """
            Perform a security-focused code review looking for:
            1. Security vulnerabilities
            2. Potential data leaks
            3. Authentication/authorization issues
            4. Input validation problems
            5. Secure coding practices
            
            Format your review as a list of comments, with each comment on a separate line.
            Lines starting with '#' will be ignored.
            """
        elif review_type == ReviewType.IMPROVE:
            return base_prompt + """
            Suggest improvements to the code focusing on:
            1. Code quality and readability
            2. Performance optimizations
            3. Better design patterns
            4. Reducing complexity
            5. Enhancing maintainability
            
            Format your suggestions as a list of comments, with each comment on a separate line.
            Lines starting with '#' will be ignored.
            """
        else:  # ReviewType.STANDARD
            return base_prompt + """
            Perform a general code review focusing on:
            1. Code correctness
            2. Readability and maintainability
            3. Adherence to best practices
            4. Potential issues or bugs
            
            Format your review as a list of comments, with each comment on a separate line.
            Lines starting with '#' will be ignored.
            """
    
    def review_pull_request(self,
                           repo_owner: str,
                           repo_name: str,
                           pr_number: int,
                           review_command: str,
                           github_token: Optional[str] = None,
                           wait_for_completion: bool = True) -> Dict[str, Any]:
        """
        Review a GitHub pull request using the specified review command.
        
        Args:
            repo_owner: GitHub repository owner (username or organization)
            repo_name: GitHub repository name
            pr_number: Pull request number
            review_command: The review command (e.g., "/review", "/gemini-review")
            github_token: GitHub token for authentication. If not provided, will try to get from GITHUB_TOKEN env var.
            wait_for_completion: Whether to wait for the review to complete
            
        Returns:
            Dictionary with results of the review operation
        """
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required. Provide it as an argument or set the GITHUB_TOKEN environment variable.")
        
        # Parse the review command
        review_type, options = self.parse_review_command(review_command)
        
        # Fetch PR data
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()
            pr_data = response.json()
            
            # Fetch PR diff
            diff_url = f"{url}.diff"
            diff_response = requests.get(diff_url, headers=headers, timeout=self.request_timeout)
            diff_response.raise_for_status()
            pr_data["diff"] = diff_response.text
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch PR data: {e}")
            return {
                "status": "error",
                "error": f"Failed to fetch PR data: {e}"
            }
        
        # Generate review prompt
        prompt = self.generate_review_prompt(review_type, pr_data, options)
        
        # Run the review task
        task_result = self.run_task(prompt, wait_for_completion=wait_for_completion)
        
        if not wait_for_completion:
            return {
                "status": "pending",
                "task_id": task_result.task_id,
                "review_type": review_type.value
            }
        
        if task_result.status != TaskStatus.COMPLETED:
            return {
                "status": "error",
                "error": task_result.error or "Review task failed",
                "task_id": task_result.task_id,
                "review_type": review_type.value
            }
        
        # Post the review comments
        comment_results = self.parse_and_post_pr_comments(
            task_result,
            repo_owner,
            repo_name,
            pr_number,
            github_token
        )
        
        return {
            "status": "completed",
            "task_id": task_result.task_id,
            "review_type": review_type.value,
            "comments": comment_results
        }
    
    def post_pr_comments(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        comments: List[str],
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post comments to a GitHub pull request, one comment per line.
        
        Args:
            repo_owner: GitHub repository owner (username or organization)
            repo_name: GitHub repository name
            pr_number: Pull request number
            comments: List of comments to post (one comment per line)
            github_token: GitHub token for authentication. If not provided, will try to get from GITHUB_TOKEN env var.
            
        Returns:
            Dictionary with results of the comment posting operation
        """
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required. Provide it as an argument or set the GITHUB_TOKEN environment variable.")
        
        # Filter out empty comments and comments starting with #
        filtered_comments = [comment for comment in comments if comment.strip() and not comment.strip().startswith('#')]
        
        if not filtered_comments:
            logger.warning("No valid comments to post after filtering")
            return {"status": "skipped", "reason": "No valid comments to post"}
        
        results = []
        for comment in filtered_comments:
            try:
                # Post the comment to the PR
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                data = {"body": comment}
                
                response = requests.post(url, headers=headers, json=data, timeout=self.request_timeout)
                response.raise_for_status()
                
                results.append({
                    "status": "success",
                    "comment_id": response.json().get("id"),
                    "comment": comment
                })
                
                logger.info(f"Posted comment to PR #{pr_number}: {comment[:50]}...")
                
                # Add a small delay to avoid rate limiting
                time.sleep(1)
                
            except requests.RequestException as e:
                logger.error(f"Failed to post comment to PR #{pr_number}: {e}")
                results.append({
                    "status": "error",
                    "error": str(e),
                    "comment": comment
                })
        
        return {
            "status": "completed",
            "total_comments": len(filtered_comments),
            "successful_comments": sum(1 for r in results if r["status"] == "success"),
            "failed_comments": sum(1 for r in results if r["status"] == "error"),
            "results": results
        }
    
    def parse_and_post_pr_comments(
        self,
        result: TaskResult,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse the result of a task and post comments to a GitHub pull request.
        
        This method will split the result into lines and post each line as a separate comment,
        ignoring lines that start with '#'.
        
        Args:
            result: The TaskResult to parse
            repo_owner: GitHub repository owner (username or organization)
            repo_name: GitHub repository name
            pr_number: Pull request number
            github_token: GitHub token for authentication. If not provided, will try to get from GITHUB_TOKEN env var.
            
        Returns:
            Dictionary with results of the comment posting operation
        """
        if not result.result:
            raise ValueError("Task result is empty")
        
        # Split the result into lines
        lines = result.result.split('\n')
        
        # Post the comments
        return self.post_pr_comments(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            comments=lines,
            github_token=github_token
        )
