#!/usr/bin/env python3
"""
Test module for code_agent.core.integration

This module tests the functionality of the integration module,
which provides utility functions to help integrate the three
main components of the CodeGen system.
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from code_agent.core.integration import (
    extract_context_for_issue_solving,
    prepare_workflow_from_issue_solution,
    generate_requirements_from_context
)


class TestIntegration(unittest.TestCase):
    """Test cases for the integration module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample context data for testing
        self.sample_context = {
            "repository": "test-repo",
            "issues": [
                {
                    "number": 123,
                    "title": "Fix login authentication bug",
                    "body": "The login authentication fails when special characters are used."
                },
                {
                    "number": 456,
                    "title": "Add user profile feature",
                    "body": "Implement a user profile page with editable fields."
                }
            ],
            "files": {
                "src/auth.py": {
                    "content": "def authenticate(username, password):\n    # Authentication logic here\n    return True"
                },
                "src/user.py": {
                    "content": "class User:\n    def __init__(self, username):\n        self.username = username"
                },
                "src/app.py": {
                    "content": "# Main application file\nfrom auth import authenticate\nfrom user import User"
                }
            },
            "error_logs": ["Error in authentication module"],
            "codebase": {
                "entry_points": ["src/app.py", "src/cli.py"]
            }
        }
        
        # Create a temporary file with the sample context
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        json.dump(self.sample_context, self.temp_file)
        self.temp_file.close()
        self.context_file_path = self.temp_file.name

    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary file
        os.unlink(self.context_file_path)

    def test_extract_context_for_issue_solving(self):
        """Test extracting context for issue solving."""
        # Test with existing issue number
        result = extract_context_for_issue_solving(self.context_file_path, 123)
        
        # Verify the result
        self.assertEqual(result['repository'], 'test-repo')
        self.assertEqual(result['issue']['number'], 123)
        self.assertEqual(result['issue']['title'], 'Fix login authentication bug')
        
        # Check if relevant code snippets were extracted
        self.assertTrue(any('auth.py' in snippet['file'] for snippet in result['code_snippets']))
        
        # Test with non-existent issue number
        result = extract_context_for_issue_solving(self.context_file_path, 999)
        self.assertEqual(result['issue'], {})
        
        # Test with invalid file path
        result = extract_context_for_issue_solving('non_existent_file.json', 123)
        self.assertEqual(result['repository'], '')
        self.assertEqual(result['issue'], {})
        self.assertEqual(result['code_snippets'], [])

    def test_prepare_workflow_from_issue_solution(self):
        """Test preparing workflow from issue solution."""
        task_id = "task-123"
        
        # Mock the open function to avoid writing to disk
        with patch('builtins.open', mock_open()) as mock_file:
            result = prepare_workflow_from_issue_solution(task_id, self.context_file_path)
        
        # Verify the result
        self.assertEqual(result['task_id'], task_id)
        self.assertEqual(result['solution_type'], 'issue')
        self.assertEqual(result['source_context'], self.context_file_path)
        self.assertEqual(result['status'], 'pending')
        
        # Test with exception
        with patch('builtins.open', side_effect=Exception("Test error")):
            result = prepare_workflow_from_issue_solution(task_id, self.context_file_path)
            self.assertEqual(result['status'], 'error')
            self.assertIn('Test error', result['error'])

    def test_generate_requirements_from_context(self):
        """Test generating requirements from context."""
        # Mock the open function to avoid writing to disk
        with patch('builtins.open', mock_open()) as mock_file:
            result = generate_requirements_from_context(self.context_file_path)
        
        # Verify the result
        self.assertIn('# Project Requirements', result)
        self.assertIn('## Issues to Resolve', result)
        self.assertIn('#123: Fix login authentication bug', result)
        self.assertIn('#456: Add user profile feature', result)
        self.assertIn('## Code Structure', result)
        self.assertIn('src/app.py', result)
        
        # Test with exception
        with patch('builtins.open', side_effect=Exception("Test error")):
            result = generate_requirements_from_context(self.context_file_path)
            self.assertIn('Error generating requirements', result)


if __name__ == '__main__':
    unittest.main()

