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
        auto_install: bool = True
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
            auto_install: Whether to automatically install the Codegen SDK if not found.
        """
        self.api_key = api_key or os.environ.get("CODEGEN_TOKEN")
        self.org_id = org_id or os.environ.get("CODEGEN_ORG_ID")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.polling_interval = polling_interval
        self.polling_timeout = polling_timeout
        
        if not self.api_key:
            raise ValueError("Codegen API key is required. Provide it as an argument or set the CODEGEN_TOKEN environment variable.")
        
        if not self.org_id:
            raise ValueError("Codegen organization ID is required. Provide it as an argument or set the CODEGEN_ORG_ID environment variable.")
        
        # Initialize the Codegen Agent
        global Agent
        if Agent is None and auto_install:
            logger.info("Codegen SDK not found. Installing...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "codegen"])
            from codegen import Agent
        
        if Agent is None:
            raise ImportError("Failed to import Codegen SDK. Please install it manually with 'pip install codegen'.")
        
        self.agent = Agent(api_key=self.api_key, org_id=self.org_id)
        logger.info(f"Initialized Codegen client with org_id={self.org_id}")
    
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
        
        # Run the task with retries
        task = None
        for attempt in range(self.max_retries):
            try:
                task = self.agent.run(prompt=prompt)
                break
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Error running Codegen task (attempt {attempt+1}/{self.max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to run Codegen task after {self.max_retries} attempts: {e}")
                    return TaskResult(
                        task_id="",
                        status=TaskStatus.FAILED,
                        error=str(e)
                    )
        
        if task is None:
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
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n\s*```', raw_result, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from code block")
        
        # Try to find any JSON object in the result
        json_match = re.search(r'({.*})', raw_result, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from matched object")
        
        # Last resort: try to parse the whole result as JSON
        try:
            return json.loads(raw_result)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from result")
            raise ValueError(f"Failed to parse JSON from result: {raw_result[:100]}...")

