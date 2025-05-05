#!/usr/bin/env python3
"""
Test script for the issue_solver module
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code_agent.core.issue_solver import IssueContext, solve_issue


class TestIssueContext(unittest.TestCase):
    """Test cases for the IssueContext class"""

    def setUp(self):
        """Set up test fixtures"""
        self.context = IssueContext()
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_repo_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    @patch('code_agent.core.issue_solver.subprocess.run')
    def test_run_command(self, mock_subprocess_run):
        """Test the _run_command method"""
        # Setup mock
        mock_process = MagicMock()
        mock_process.stdout = "test output"
        mock_subprocess_run.return_value = mock_process

        # Run the method
        result = self.context._run_command("test command")

        # Assertions
        mock_subprocess_run.assert_called_once_with(
            "test command",
            shell=True,
            check=False,
            stdout=-1,  # subprocess.PIPE
            stderr=-1,  # subprocess.PIPE
            text=True
        )
        self.assertEqual(result, "test output")

    @patch('code_agent.core.issue_solver.subprocess.run')
    def test_command_exists_true(self, mock_subprocess_run):
        """Test the _command_exists method when command exists"""
        # Setup mock to return success
        mock_subprocess_run.return_value.returncode = 0

        # Run the method
        result = self.context._command_exists("existing_command")

        # Assertions
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once()

    @patch('code_agent.core.issue_solver.subprocess.run')
    def test_command_exists_false(self, mock_subprocess_run):
        """Test the _command_exists method when command doesn't exist"""
        # Setup mock to raise CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "which non_existing_command")

        # Run the method
        result = self.context._command_exists("non_existing_command")

        # Assertions
        self.assertFalse(result)

    @patch('code_agent.core.issue_solver.IssueContext._run_command')
    def test_collect_repo_info(self, mock_run_command):
        """Test the collect_repo_info method"""
        # Setup mocks
        mock_run_command.side_effect = [
            "https://github.com/Zeeeepa/Code_agent.git",  # git config
            "main"  # git rev-parse
        ]

        # Run the method
        self.context.collect_repo_info()

        # Assertions
        self.assertEqual(self.context.context["repository"], "Zeeeepa/Code_agent")
        self.assertEqual(self.context.context["branch"], "main")
        self.assertEqual(mock_run_command.call_count, 2)

    @patch('code_agent.core.issue_solver.IssueContext._command_exists')
    @patch('code_agent.core.issue_solver.IssueContext._run_command')
    def test_collect_issue_info_with_gh(self, mock_run_command, mock_command_exists):
        """Test the collect_issue_info method with GitHub CLI available"""
        # Setup mocks
        mock_command_exists.return_value = True
        issue_data = {
            "title": "Test Issue",
            "body": "This is a test issue",
            "labels": ["bug"],
            "assignees": ["user1"],
            "comments": []
        }
        mock_run_command.return_value = json.dumps(issue_data)

        # Run the method
        self.context.collect_issue_info(123)

        # Assertions
        self.assertEqual(self.context.context["issue"], issue_data)
        mock_command_exists.assert_called_once_with("gh")
        mock_run_command.assert_called_once_with("gh issue view 123 --json title,body,labels,assignees,comments")

    @patch('code_agent.core.issue_solver.IssueContext._command_exists')
    def test_collect_issue_info_without_gh(self, mock_command_exists):
        """Test the collect_issue_info method without GitHub CLI"""
        # Setup mocks
        mock_command_exists.return_value = False

        # Run the method
        self.context.collect_issue_info(123)

        # Assertions
        expected_issue = {
            "number": 123,
            "title": "Unknown issue",
            "body": "Could not fetch issue details - GitHub CLI not available"
        }
        self.assertEqual(self.context.context["issue"], expected_issue)
        mock_command_exists.assert_called_once_with("gh")

    @patch('code_agent.core.issue_solver.IssueContext._run_command')
    @patch('builtins.open', new_callable=mock_open, read_data="test file content")
    def test_find_relevant_code(self, mock_file_open, mock_run_command):
        """Test the find_relevant_code method"""
        # Setup mocks
        mock_run_command.return_value = "file1.py\nfile2.py\n"

        # Run the method
        self.context.find_relevant_code(["keyword1", "keyword2"])

        # Assertions
        self.assertEqual(len(self.context.context["code_snippets"]), 2)
        self.assertEqual(self.context.context["code_snippets"][0]["file"], "file1.py")
        self.assertEqual(self.context.context["code_snippets"][0]["content"], "test file content")
        self.assertEqual(self.context.context["code_snippets"][1]["file"], "file2.py")
        self.assertEqual(self.context.context["code_snippets"][1]["content"], "test file content")

        # Check that grep command was constructed correctly
        expected_grep_cmd = "grep -r --include=*.py --include=*.js --include=*.ts --include=*.jsx --include=*.tsx --include=*.go --include=*.java --include=*.rb -l -E 'keyword1|keyword2' ."
        mock_run_command.assert_called_once_with(expected_grep_cmd)

    @patch('code_agent.core.issue_solver.IssueContext._run_command')
    @patch('builtins.open', new_callable=mock_open, read_data="ERROR: test error")
    def test_find_error_logs(self, mock_file_open, mock_run_command):
        """Test the find_error_logs method"""
        # Setup mocks
        mock_run_command.side_effect = [
            "log1.log\nlog2.log\n",  # find command
            "ERROR: test error\n"  # grep command for log1.log
        ]

        # Run the method
        self.context.find_error_logs()

        # Assertions
        self.assertEqual(len(self.context.context["error_logs"]), 1)
        self.assertEqual(self.context.context["error_logs"][0]["file"], "log1.log")
        self.assertEqual(self.context.context["error_logs"][0]["content"], "ERROR: test error\n")

    def test_extract_keywords(self):
        """Test the extract_keywords method"""
        # Setup test data
        self.context.context["issue"] = {
            "title": "Fix the authentication bug in login module",
            "body": "When trying to login, I get the following error: `AuthenticationError: Invalid credentials`.\n\nThis happens in the `authenticate_user` function."
        }

        # Run the method
        keywords = self.context.extract_keywords()

        # Assertions
        expected_keywords = [
            "authentication", "login", "module", "authenticationerror", "invalid", "credentials", "authenticate_user"
        ]
        # Check that all expected keywords are in the result (order may vary)
        for keyword in expected_keywords:
            self.assertIn(keyword, keywords)

    def test_create_prompt_bug(self):
        """Test the create_prompt method for bug task"""
        # Setup test data
        self.context.context = {
            "repository": "Zeeeepa/Code_agent",
            "branch": "main",
            "issue": {
                "number": 123,
                "title": "Authentication Bug",
                "body": "Login fails with invalid credentials error"
            },
            "code_snippets": [
                {
                    "file": "auth.py",
                    "content": "def authenticate_user(username, password):\n    # Authentication logic\n    pass"
                }
            ],
            "error_logs": [
                {
                    "file": "app.log",
                    "content": "ERROR: Authentication failed for user 'test'"
                }
            ]
        }

        # Run the method
        prompt = self.context.create_prompt("bug")

        # Assertions
        self.assertIn("Bug Fix Task", prompt)
        self.assertIn("Repository: Zeeeepa/Code_agent", prompt)
        self.assertIn("Issue: #123 - Authentication Bug", prompt)
        self.assertIn("Login fails with invalid credentials error", prompt)
        self.assertIn("auth.py", prompt)
        self.assertIn("def authenticate_user", prompt)
        self.assertIn("app.log", prompt)
        self.assertIn("ERROR: Authentication failed", prompt)

    def test_create_prompt_feature(self):
        """Test the create_prompt method for feature task"""
        # Setup test data
        self.context.context = {
            "repository": "Zeeeepa/Code_agent",
            "branch": "main",
            "issue": {
                "number": 124,
                "title": "Add user profile page",
                "body": "We need to add a user profile page"
            },
            "code_snippets": [],
            "error_logs": []
        }

        # Run the method
        prompt = self.context.create_prompt("feature")

        # Assertions
        self.assertIn("Feature Implementation Task", prompt)
        self.assertIn("Repository: Zeeeepa/Code_agent", prompt)
        self.assertIn("Issue: #124 - Add user profile page", prompt)
        self.assertIn("We need to add a user profile page", prompt)

    @patch('builtins.open', new_callable=mock_open)
    def test_save_context(self, mock_file_open):
        """Test the save_context method"""
        # Setup test data
        self.context.context = {"test": "data"}

        # Run the method
        self.context.save_context("test_context.json")

        # Assertions
        mock_file_open.assert_called_once_with("test_context.json", 'w', encoding='utf-8')
        mock_file_open().write.assert_called_once()
        # Check that json.dump was called with the correct data
        written_data = mock_file_open().write.call_args[0][0]
        self.assertIn('"test": "data"', written_data)


class TestSolveIssue(unittest.TestCase):
    """Test cases for the solve_issue function"""

    @patch('code_agent.core.issue_solver.Agent')
    @patch('code_agent.core.issue_solver.IssueContext')
    @patch('builtins.open', new_callable=mock_open)
    def test_solve_issue_success(self, mock_file_open, MockIssueContext, MockAgent):
        """Test the solve_issue function with successful execution"""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.extract_keywords.return_value = ["keyword1", "keyword2"]
        mock_context.create_prompt.return_value = "Test prompt"
        MockIssueContext.return_value = mock_context

        mock_agent = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "task123"
        mock_task.status = "completed"
        mock_agent.run.return_value = mock_task
        MockAgent.return_value = mock_agent

        # Run the function
        result = solve_issue(123, "bug", "org123", "token123")

        # Assertions
        self.assertEqual(result, "task123")
        mock_context.collect_repo_info.assert_called_once()
        mock_context.collect_issue_info.assert_called_once_with(123)
        mock_context.extract_keywords.assert_called_once()
        mock_context.find_relevant_code.assert_called_once()
        mock_context.find_error_logs.assert_called_once()
        mock_context.save_context.assert_called_once()
        mock_context.create_prompt.assert_called_once_with("bug")
        MockAgent.assert_called_once_with(org_id="org123", token="token123")
        mock_agent.run.assert_called_once_with(prompt="Test prompt")
        mock_task.refresh.assert_called_once()

    @patch('code_agent.core.issue_solver.Agent')
    @patch('code_agent.core.issue_solver.IssueContext')
    @patch('builtins.open', new_callable=mock_open)
    def test_solve_issue_failure(self, mock_file_open, MockIssueContext, MockAgent):
        """Test the solve_issue function with failed execution"""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.extract_keywords.return_value = ["keyword1", "keyword2"]
        mock_context.create_prompt.return_value = "Test prompt"
        MockIssueContext.return_value = mock_context

        mock_agent = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "task123"
        mock_task.status = "failed"
        mock_task.error = "Test error"
        mock_agent.run.return_value = mock_task
        MockAgent.return_value = mock_agent

        # Run the function
        result = solve_issue(123, "bug", "org123", "token123")

        # Assertions
        self.assertIsNone(result)
        mock_context.collect_repo_info.assert_called_once()
        mock_context.collect_issue_info.assert_called_once_with(123)
        mock_context.extract_keywords.assert_called_once()
        mock_context.find_relevant_code.assert_called_once()
        mock_context.find_error_logs.assert_called_once()
        mock_context.save_context.assert_called_once()
        mock_context.create_prompt.assert_called_once_with("bug")
        MockAgent.assert_called_once_with(org_id="org123", token="token123")
        mock_agent.run.assert_called_once_with(prompt="Test prompt")
        mock_task.refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()

