"""
Tests for the Codegen client module.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os

from code_agent.core.codegen_client import CodegenClient, TaskStatus, TaskResult

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

if __name__ == '__main__':
    unittest.main()

