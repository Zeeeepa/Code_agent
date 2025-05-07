"""
Tests for the Codegen client module.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
import time
import requests

from code_agent.core.codegen_client import CodegenClient, TaskStatus, TaskResult, CircuitBreaker, CircuitBreakerState, ReviewType

class TestCircuitBreaker(unittest.TestCase):
    """Test cases for the CircuitBreaker class."""
    
    def setUp(self):
        """Set up test environment."""
        self.circuit = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1  # Short timeout for testing
        )
    
    def test_initial_state(self):
        """Test initial state of the circuit breaker."""
        self.assertEqual(self.circuit.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit.failure_count, 0)
        self.assertTrue(self.circuit.allow_request())
    
    def test_open_circuit(self):
        """Test opening the circuit after threshold failures."""
        # Record failures up to threshold
        for _ in range(3):
            self.circuit.record_failure()
        
        # Circuit should be open now
        self.assertEqual(self.circuit.state, CircuitBreakerState.OPEN)
        self.assertFalse(self.circuit.allow_request())
    
    def test_half_open_after_timeout(self):
        """Test transition to half-open state after timeout."""
        # Open the circuit
        for _ in range(3):
            self.circuit.record_failure()
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Circuit should allow one request (half-open)
        self.assertTrue(self.circuit.allow_request())
        self.assertEqual(self.circuit.state, CircuitBreakerState.HALF_OPEN)
    
    def test_close_after_success(self):
        """Test closing the circuit after successful request in half-open state."""
        # Open the circuit
        for _ in range(3):
            self.circuit.record_failure()
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Circuit should be half-open
        self.assertTrue(self.circuit.allow_request())
        self.assertEqual(self.circuit.state, CircuitBreakerState.HALF_OPEN)
        
        # Record success
        self.circuit.record_success()
        
        # Circuit should be closed
        self.assertEqual(self.circuit.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit.failure_count, 0)
    
    def test_reopen_after_failure_in_half_open(self):
        """Test reopening the circuit after failure in half-open state."""
        # Open the circuit
        for _ in range(3):
            self.circuit.record_failure()
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Circuit should be half-open
        self.assertTrue(self.circuit.allow_request())
        self.assertEqual(self.circuit.state, CircuitBreakerState.HALF_OPEN)
        
        # Record failure
        self.circuit.record_failure()
        
        # Circuit should be open again
        self.assertEqual(self.circuit.state, CircuitBreakerState.OPEN)
        self.assertFalse(self.circuit.allow_request())

class TestCodegenClient(unittest.TestCase):
    """Test cases for the CodegenClient class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            "CODEGEN_TOKEN": "test-token",
            "CODEGEN_ORG_ID": "test-org-id"
        })
        self.env_patcher.start()
        
        # Mock the Agent class
        self.agent_patcher = patch('code_agent.core.codegen_client.Agent')
        self.mock_agent_class = self.agent_patcher.start()
        self.mock_agent = MagicMock()
        self.mock_agent_class.return_value = self.mock_agent
        
        # Create a client instance
        self.client = CodegenClient(
            polling_interval=0.1,  # Use small values for testing
            polling_timeout=1.0
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        self.agent_patcher.stop()
    
    def test_initialization(self):
        """Test client initialization."""
        # Check that the client was initialized with the correct values
        self.assertEqual(self.client.api_key, "test-token")
        self.assertEqual(self.client.org_id, "test-org-id")
        
        # Check that the Agent was initialized correctly
        self.mock_agent_class.assert_called_once_with(
            api_key="test-token",
            org_id="test-org-id"
        )
    
    def test_initialization_with_args(self):
        """Test client initialization with explicit arguments."""
        client = CodegenClient(
            api_key="arg-token",
            org_id="arg-org-id"
        )
        
        # Check that the client was initialized with the correct values
        self.assertEqual(client.api_key, "arg-token")
        self.assertEqual(client.org_id, "arg-org-id")
    
    def test_initialization_with_env_vars(self):
        """Test client initialization with alternative environment variables."""
        # Set up environment variables
        with patch.dict(os.environ, {
            "CODEGEN_TOKEN": None,
            "CODEGEN_API_KEY": "env-api-key",
            "CODEGEN_ORG_ID": None,
            "CODEGEN_ORGANIZATION_ID": "env-org-id",
            "CODEGEN_MAX_RETRIES": "5",
            "CODEGEN_RETRY_DELAY": "3.0",
            "CODEGEN_POLLING_INTERVAL": "15.0",
            "CODEGEN_POLLING_TIMEOUT": "600.0",
            "CODEGEN_REQUEST_TIMEOUT": "45.0",
            "CODEGEN_CIRCUIT_BREAKER_THRESHOLD": "10",
            "CODEGEN_CIRCUIT_BREAKER_RECOVERY_TIME": "120.0"
        }):
            client = CodegenClient()
            
            # Check that the client was initialized with the correct values
            self.assertEqual(client.api_key, "env-api-key")
            self.assertEqual(client.org_id, "env-org-id")
            self.assertEqual(client.max_retries, 5)
            self.assertEqual(client.retry_delay, 3.0)
            self.assertEqual(client.polling_interval, 15.0)
            self.assertEqual(client.polling_timeout, 600.0)
            self.assertEqual(client.request_timeout, 45.0)
            self.assertEqual(client.circuit_breaker.failure_threshold, 10)
            self.assertEqual(client.circuit_breaker.recovery_timeout, 120.0)
    
    def test_validate_prompt(self):
        """Test prompt validation."""
        # Valid prompt
        self.client._validate_prompt("This is a valid prompt")
        
        # Empty prompt
        with self.assertRaises(ValueError):
            self.client._validate_prompt("")
        
        # Too long prompt
        with self.assertRaises(ValueError):
            self.client._validate_prompt("x" * 33000)
    
    def test_calculate_retry_delay(self):
        """Test retry delay calculation."""
        # Test without jitter
        self.assertEqual(self.client._calculate_retry_delay(0, jitter=False), 2.0)
        self.assertEqual(self.client._calculate_retry_delay(1, jitter=False), 4.0)
        self.assertEqual(self.client._calculate_retry_delay(2, jitter=False), 8.0)
        
        # Test with jitter (should be in range)
        delay = self.client._calculate_retry_delay(0, jitter=True)
        self.assertTrue(1.0 <= delay <= 4.0)
    
    def test_run_task_success(self):
        """Test running a task successfully."""
        # Mock the task
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = "completed"
        mock_task.result = "Task result"
        
        # Configure the mock agent to return the mock task
        self.mock_agent.run.return_value = mock_task
        
        # Run the task
        result = self.client.run_task("Test prompt", wait_for_completion=False)
        
        # Check that the agent was called correctly
        self.mock_agent.run.assert_called_once_with(prompt="Test prompt")
        
        # Check the result
        self.assertEqual(result.task_id, "test-task-id")
        self.assertEqual(result.status, TaskStatus.PENDING)
    
    def test_run_task_with_polling(self):
        """Test running a task with polling for completion."""
        # Mock the task
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = "running"  # Initial status
        mock_task.result = "Task result"
        
        # Configure the mock agent to return the mock task
        self.mock_agent.run.return_value = mock_task
        
        # Configure the task to change status after refresh
        def update_status():
            mock_task.status = "completed"
        mock_task.refresh.side_effect = update_status
        
        # Run the task
        result = self.client.run_task("Test prompt")
        
        # Check that the agent was called correctly
        self.mock_agent.run.assert_called_once_with(prompt="Test prompt")
        
        # Check that refresh was called
        mock_task.refresh.assert_called()
        
        # Check the result
        self.assertEqual(result.task_id, "test-task-id")
        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertEqual(result.result, "Task result")
    
    def test_run_task_failure(self):
        """Test handling a failed task."""
        # Mock the task
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = "running"  # Initial status
        mock_task.error = "Task failed"
        
        # Configure the mock agent to return the mock task
        self.mock_agent.run.return_value = mock_task
        
        # Configure the task to change status after refresh
        def update_status():
            mock_task.status = "failed"
        mock_task.refresh.side_effect = update_status
        
        # Run the task
        result = self.client.run_task("Test prompt")
        
        # Check the result
        self.assertEqual(result.task_id, "test-task-id")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertEqual(result.error, "Task failed")
    
    def test_run_task_timeout(self):
        """Test handling a task timeout."""
        # Mock the task
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = "running"  # Status never changes
        
        # Configure the mock agent to return the mock task
        self.mock_agent.run.return_value = mock_task
        
        # Run the task (should timeout quickly due to our short polling_timeout)
        result = self.client.run_task("Test prompt")
        
        # Check the result
        self.assertEqual(result.task_id, "test-task-id")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertTrue("timed out" in result.error)
    
    def test_run_task_with_circuit_breaker(self):
        """Test running a task with circuit breaker."""
        # Mock the agent to raise an exception
        self.mock_agent.run.side_effect = Exception("API error")
        
        # Run the task multiple times to trigger circuit breaker
        for _ in range(5):
            result = self.client.run_task("Test prompt")
            self.assertEqual(result.status, TaskStatus.FAILED)
        
        # Circuit should be open now
        self.assertEqual(self.client.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Next request should be blocked by circuit breaker
        result = self.client.run_task("Test prompt")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertTrue("Service is currently unavailable" in result.error)
        
        # Mock agent should not have been called again
        self.assertEqual(self.mock_agent.run.call_count, 5 * self.client.max_retries)
    
    def test_run_task_with_invalid_prompt(self):
        """Test running a task with an invalid prompt."""
        # Run the task with an empty prompt
        result = self.client.run_task("")
        
        # Check the result
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertTrue("Prompt cannot be empty" in result.error)
        
        # Agent should not have been called
        self.mock_agent.run.assert_not_called()
    
    def test_parse_json_result_code_block(self):
        """Test parsing JSON from a code block."""
        # Create a task result with JSON in a code block
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result="""
            Here's the result:
            
            ```json
            {
                "key": "value",
                "number": 42
            }
            ```
            """
        )
        
        # Parse the JSON
        result = self.client.parse_json_result(task_result)
        
        # Check the result
        self.assertEqual(result, {"key": "value", "number": 42})
    
    def test_parse_json_result_object(self):
        """Test parsing JSON from an object in the result."""
        # Create a task result with a JSON object
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result="""
            Here's the result:
            
            {"key": "value", "number": 42}
            
            Hope that helps!
            """
        )
        
        # Parse the JSON
        result = self.client.parse_json_result(task_result)
        
        # Check the result
        self.assertEqual(result, {"key": "value", "number": 42})
    
    def test_parse_json_result_direct(self):
        """Test parsing JSON directly from the result."""
        # Create a task result with direct JSON
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result='{"key": "value", "number": 42}'
        )
        
        # Parse the JSON
        result = self.client.parse_json_result(task_result)
        
        # Check the result
        self.assertEqual(result, {"key": "value", "number": 42})
    
    def test_parse_json_result_with_comments(self):
        """Test parsing JSON with comment lines."""
        # Create a task result with JSON and comment lines
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result="""
            # This is a comment
            {"key": "value", "number": 42}
            # This is another comment
            """
        )
        
        # Parse the JSON
        result = self.client.parse_json_result(task_result)
        
        # Check the result
        self.assertEqual(result, {"key": "value", "number": 42})
    
    def test_parse_json_result_error(self):
        """Test handling a JSON parsing error."""
        # Create a task result with invalid JSON
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result="This is not JSON"
        )
        
        # Try to parse the JSON (should raise an error)
        with self.assertRaises(ValueError):
            self.client.parse_json_result(task_result)

class TestPRReviewFunctionality(unittest.TestCase):
    """Test cases for the PR review functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            "CODEGEN_TOKEN": "test-token",
            "CODEGEN_ORG_ID": "test-org-id",
            "GITHUB_TOKEN": "test-github-token"
        })
        self.env_patcher.start()
        
        # Mock the Agent class
        self.agent_patcher = patch('code_agent.core.codegen_client.Agent')
        self.mock_agent_class = self.agent_patcher.start()
        self.mock_agent = MagicMock()
        self.mock_agent_class.return_value = self.mock_agent
        
        # Mock requests
        self.requests_patcher = patch('code_agent.core.codegen_client.requests')
        self.mock_requests = self.requests_patcher.start()
        
        # Create a client instance
        self.client = CodegenClient(
            polling_interval=0.1,  # Use small values for testing
            polling_timeout=1.0
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        self.agent_patcher.stop()
        self.requests_patcher.stop()
    
    def test_parse_review_command(self):
        """Test parsing different review commands."""
        # Test standard review
        review_type, options = self.client.parse_review_command("/review")
        self.assertEqual(review_type, ReviewType.STANDARD)
        
        # Test Gemini review
        review_type, options = self.client.parse_review_command("/gemini-review")
        self.assertEqual(review_type, ReviewType.GEMINI)
        
        # Test Korbit review
        review_type, options = self.client.parse_review_command("/korbit-review")
        self.assertEqual(review_type, ReviewType.KORBIT)
        
        # Test improve command
        review_type, options = self.client.parse_review_command("/improve")
        self.assertEqual(review_type, ReviewType.IMPROVE)
        
        # Test with whitespace
        review_type, options = self.client.parse_review_command("  /gemini-review  ")
        self.assertEqual(review_type, ReviewType.GEMINI)
        
        # Test with uppercase
        review_type, options = self.client.parse_review_command("/GEMINI-REVIEW")
        self.assertEqual(review_type, ReviewType.GEMINI)
    
    def test_generate_review_prompt(self):
        """Test generating review prompts for different review types."""
        pr_data = {
            "title": "Test PR",
            "body": "This is a test PR",
            "diff": "diff --git a/test.py b/test.py\n..."
        }
        
        # Test standard review prompt
        prompt = self.client.generate_review_prompt(ReviewType.STANDARD, pr_data)
        self.assertIn("Test PR", prompt)
        self.assertIn("This is a test PR", prompt)
        self.assertIn("general code review", prompt.lower())
        
        # Test Gemini review prompt
        prompt = self.client.generate_review_prompt(ReviewType.GEMINI, pr_data)
        self.assertIn("Test PR", prompt)
        self.assertIn("thorough code review", prompt.lower())
        self.assertIn("security vulnerabilities", prompt.lower())
        
        # Test Korbit review prompt
        prompt = self.client.generate_review_prompt(ReviewType.KORBIT, pr_data)
        self.assertIn("Test PR", prompt)
        self.assertIn("security-focused", prompt.lower())
        self.assertIn("authentication/authorization", prompt.lower())
        
        # Test improve prompt
        prompt = self.client.generate_review_prompt(ReviewType.IMPROVE, pr_data)
        self.assertIn("Test PR", prompt)
        self.assertIn("suggest improvements", prompt.lower())
        self.assertIn("performance optimizations", prompt.lower())
    
    def test_post_pr_comments(self):
        """Test posting comments to a PR."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 12345}
        self.mock_requests.post.return_value = mock_response
        
        # Test posting comments
        result = self.client.post_pr_comments(
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=1,
            comments=["Comment 1", "# Comment 2 (should be ignored)", "Comment 3"]
        )
        
        # Check that the correct number of comments were posted
        self.assertEqual(result["total_comments"], 2)
        self.assertEqual(result["successful_comments"], 2)
        self.assertEqual(result["failed_comments"], 0)
        
        # Check that the correct API calls were made
        self.assertEqual(self.mock_requests.post.call_count, 2)
        self.mock_requests.post.assert_any_call(
            "https://api.github.com/repos/test-owner/test-repo/issues/1/comments",
            headers={
                "Authorization": "token test-github-token",
                "Accept": "application/vnd.github.v3+json"
            },
            json={"body": "Comment 1"},
            timeout=self.client.request_timeout
        )
    
    def test_parse_and_post_pr_comments(self):
        """Test parsing and posting comments from a task result."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 12345}
        self.mock_requests.post.return_value = mock_response
        
        # Create a task result
        task_result = TaskResult(
            task_id="test-task-id",
            status=TaskStatus.COMPLETED,
            result="Comment 1\n# Comment 2 (should be ignored)\nComment 3"
        )
        
        # Test parsing and posting comments
        result = self.client.parse_and_post_pr_comments(
            result=task_result,
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=1
        )
        
        # Check that the correct number of comments were posted
        self.assertEqual(result["total_comments"], 2)
        self.assertEqual(result["successful_comments"], 2)
        self.assertEqual(result["failed_comments"], 0)
        
        # Check that the correct API calls were made
        self.assertEqual(self.mock_requests.post.call_count, 2)
    
    def test_review_pull_request(self):
        """Test reviewing a pull request."""
        # Mock PR data response
        mock_pr_response = MagicMock()
        mock_pr_response.json.return_value = {
            "title": "Test PR",
            "body": "This is a test PR"
        }
        
        # Mock PR diff response
        mock_diff_response = MagicMock()
        mock_diff_response.text = "diff --git a/test.py b/test.py\n..."
        
        # Mock comment response
        mock_comment_response = MagicMock()
        mock_comment_response.json.return_value = {"id": 12345}
        
        # Configure mock requests
        self.mock_requests.get.side_effect = [mock_pr_response, mock_diff_response]
        self.mock_requests.post.return_value = mock_comment_response
        
        # Mock task
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = "completed"
        mock_task.result = "Comment 1\n# Comment 2 (should be ignored)\nComment 3"
        
        # Configure the mock agent
        self.mock_agent.run.return_value = mock_task
        
        # Test reviewing a PR
        result = self.client.review_pull_request(
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=1,
            review_command="/gemini-review"
        )
        
        # Check the result
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_id"], "test-task-id")
        self.assertEqual(result["review_type"], "gemini")
        self.assertEqual(result["comments"]["total_comments"], 2)
        
        # Check that the correct API calls were made
        self.mock_requests.get.assert_any_call(
            "https://api.github.com/repos/test-owner/test-repo/pulls/1",
            headers={
                "Authorization": "token test-github-token",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=self.client.request_timeout
        )
        
        # Check that the agent was called with the correct prompt
        self.mock_agent.run.assert_called_once()
        prompt = self.mock_agent.run.call_args[1]["prompt"]
        self.assertIn("Test PR", prompt)
        self.assertIn("This is a test PR", prompt)
        self.assertIn("thorough code review", prompt.lower())

if __name__ == '__main__':
    unittest.main()
