#!/usr/bin/env python3
"""
Test suite for the Code Agent Runner module
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace

# Add the parent directory to sys.path to allow importing the code_agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code_agent.runner import main


class TestRunner:
    """Test cases for the runner.py module"""

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch('code_agent.core.issue_solver.solve_issue')
    def test_issue_mode_success(self, mock_solve_issue, mock_parse_known_args, mock_parse_args):
        """Test the issue mode with successful execution"""
        # Mock the arguments
        mock_args = Namespace(
            mode='issue',
            issue_number=123,
            task_type='bug',
            org_id='test-org-id',
            token='test-token'
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Mock the solve_issue function to return a task ID
        mock_solve_issue.return_value = 'task-123'
        
        # Call the main function
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_not_called()
        
        # Verify that solve_issue was called with the correct arguments
        mock_solve_issue.assert_called_once_with(123, 'bug', 'test-org-id', 'test-token')

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch('code_agent.core.issue_solver.solve_issue')
    def test_issue_mode_failure(self, mock_solve_issue, mock_parse_known_args, mock_parse_args):
        """Test the issue mode with failed execution"""
        # Mock the arguments
        mock_args = Namespace(
            mode='issue',
            issue_number=123,
            task_type='bug',
            org_id='test-org-id',
            token='test-token'
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Mock the solve_issue function to return None (failure)
        mock_solve_issue.return_value = None
        
        # Call the main function
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    def test_issue_mode_missing_credentials(self, mock_parse_known_args, mock_parse_args):
        """Test the issue mode with missing credentials"""
        # Mock the arguments with missing credentials
        mock_args = Namespace(
            mode='issue',
            issue_number=123,
            task_type='bug',
            org_id=None,
            token=None
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Ensure environment variables are not set
        with patch.dict(os.environ, {}, clear=True):
            # Call the main function
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch('code_agent.core.context_manager.main')
    def test_context_mode(self, mock_context_main, mock_parse_known_args, mock_parse_args):
        """Test the context mode"""
        # Mock the arguments
        mock_args = Namespace(
            mode='context',
            command='collect',
            output='context.json',
            issue=None,
            pr=None,
            max_files=20,
            file_patterns=None,
            exclude_patterns=None
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Call the main function
        with patch('sys.argv', ['code_agent.runner', 'collect']):
            main()
        
        # Verify that context_main was called
        mock_context_main.assert_called_once()

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch('code_agent.core.workflow.main')
    def test_workflow_mode(self, mock_workflow_main, mock_parse_known_args, mock_parse_args):
        """Test the workflow mode"""
        # Mock the arguments
        mock_args = Namespace(
            mode='workflow',
            github_token='github-token',
            ngrok_token='ngrok-token',
            repo_name='owner/repo',
            codegen_token='codegen-token',
            codegen_org_id='codegen-org-id',
            webhook_port=5000
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Call the main function
        with patch('sys.argv', ['code_agent.runner']):
            main()
        
        # Verify that workflow_main was called
        mock_workflow_main.assert_called_once()

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    def test_invalid_mode(self, mock_parse_known_args, mock_parse_args):
        """Test with an invalid mode (should never happen due to argparse choices, but testing for completeness)"""
        # Mock the arguments with an invalid mode
        mock_args = Namespace(
            mode='invalid'
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Call the main function
        with patch('sys.exit') as mock_exit:
            main()
            # The function should exit with an error
            assert mock_exit.called

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch('code_agent.core.issue_solver.solve_issue')
    def test_exception_handling(self, mock_solve_issue, mock_parse_known_args, mock_parse_args):
        """Test exception handling in the main function"""
        # Mock the arguments
        mock_args = Namespace(
            mode='issue',
            issue_number=123,
            task_type='bug',
            org_id='test-org-id',
            token='test-token'
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Mock the solve_issue function to raise an exception
        mock_solve_issue.side_effect = Exception("Test exception")
        
        # Call the main function
        with patch('sys.exit') as mock_exit:
            with patch('traceback.print_exc') as mock_traceback:
                main()
                mock_exit.assert_called_once_with(1)
                mock_traceback.assert_called_once()

    @patch('code_agent.runner.argparse.ArgumentParser.parse_args')
    @patch('code_agent.runner.argparse.ArgumentParser.parse_known_args')
    @patch.dict(os.environ, {"CODEGEN_ORG_ID": "env-org-id", "CODEGEN_TOKEN": "env-token"})
    @patch('code_agent.core.issue_solver.solve_issue')
    def test_issue_mode_env_credentials(self, mock_solve_issue, mock_parse_known_args, mock_parse_args):
        """Test the issue mode with credentials from environment variables"""
        # Mock the arguments with missing credentials (should be taken from env)
        mock_args = Namespace(
            mode='issue',
            issue_number=123,
            task_type='bug',
            org_id=None,
            token=None
        )
        mock_parse_known_args.return_value = (mock_args, [])
        mock_parse_args.return_value = mock_args
        
        # Mock the solve_issue function to return a task ID
        mock_solve_issue.return_value = 'task-123'
        
        # Call the main function
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_not_called()
        
        # Verify that solve_issue was called with the correct arguments from env vars
        mock_solve_issue.assert_called_once_with(123, 'bug', 'env-org-id', 'env-token')


if __name__ == "__main__":
    pytest.main(["-v", __file__])

