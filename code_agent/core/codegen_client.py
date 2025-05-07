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
from typing import Dict, Any, Optional, List, Union, Callable
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
