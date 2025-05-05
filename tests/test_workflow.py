#!/usr/bin/env python3
"""
Test suite for the Code Agent Workflow Manager
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import threading
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code_agent.core.workflow import (
    Configuration, 
    GitHubManager, 
    NgrokManager, 
    CodeGenManager, 
    DeploymentManager, 
    WebhookServer, 
    WorkflowManager
)


class TestConfiguration(unittest.TestCase):
    """Test cases for the Configuration class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a fresh config instance for each test
        self.config = Configuration()
        
        # Save original environment variables to restore later
        self.original_env = os.environ.copy()
        
        # Clear relevant environment variables for testing
        for var in ['GITHUB_TOKEN', 'NGROK_TOKEN', 'REPO_NAME', 
                    'CODEGEN_TOKEN', 'CODEGEN_ORG_ID']:
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up after each test."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_initialization(self):
        """Test that the config initializes with default values."""
        config = Configuration()
        
        # Check default values
        self.assertEqual(config.github_token, "")
        self.assertEqual(config.ngrok_token, "")
        self.assertEqual(config.repo_name, "")
        self.assertEqual(config.codegen_token, "")
        self.assertEqual(config.codegen_org_id, "")
        self.assertEqual(config.webhook_url, "")
        self.assertEqual(config.webhook_port, 5000)
        self.assertEqual(config.webhook_path, "/webhook")
        self.assertEqual(config.requirements_path, "REQUIREMENTS.md")
        self.assertEqual(config.test_branch_prefix, "test-")
        self.assertEqual(config.deployment_script_path, "deploy.py")

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ['GITHUB_TOKEN'] = 'test_github_token'
        os.environ['NGROK_TOKEN'] = 'test_ngrok_token'
        os.environ['REPO_NAME'] = 'test/repo'
        os.environ['CODEGEN_TOKEN'] = 'test_codegen_token'
        os.environ['CODEGEN_ORG_ID'] = 'test_codegen_org_id'
        
        # Load from environment
        self.config.load_from_env()
        
        # Check that values were loaded from environment
        self.assertEqual(self.config.github_token, 'test_github_token')
        self.assertEqual(self.config.ngrok_token, 'test_ngrok_token')
        self.assertEqual(self.config.repo_name, 'test/repo')
        self.assertEqual(self.config.codegen_token, 'test_codegen_token')
        self.assertEqual(self.config.codegen_org_id, 'test_codegen_org_id')

    def test_load_from_args(self):
        """Test loading configuration from command line arguments."""
        # Create mock args
        args = MagicMock()
        args.github_token = 'args_github_token'
        args.ngrok_token = 'args_ngrok_token'
        args.repo_name = 'args/repo'
        args.codegen_token = 'args_codegen_token'
        args.codegen_org_id = 'args_codegen_org_id'
        args.webhook_port = 8080
        
        # Load from args
        self.config.load_from_args(args)
        
        # Check that values were loaded from args
        self.assertEqual(self.config.github_token, 'args_github_token')
        self.assertEqual(self.config.ngrok_token, 'args_ngrok_token')
        self.assertEqual(self.config.repo_name, 'args/repo')
        self.assertEqual(self.config.codegen_token, 'args_codegen_token')
        self.assertEqual(self.config.codegen_org_id, 'args_codegen_org_id')
        self.assertEqual(self.config.webhook_port, 8080)

    def test_validate(self):
        """Test configuration validation."""
        # Empty config should have validation errors
        errors = self.config.validate()
        self.assertEqual(len(errors), 5)
        self.assertIn("GitHub token is not provided", errors)
        self.assertIn("ngrok token is not provided", errors)
        self.assertIn("Repository name is not provided", errors)
        self.assertIn("CodeGen token is not provided", errors)
        self.assertIn("CodeGen organization ID is not provided", errors)
        
        # Set required values
        self.config.github_token = 'valid_github_token'
        self.config.ngrok_token = 'valid_ngrok_token'
        self.config.repo_name = 'valid/repo'
        self.config.codegen_token = 'valid_codegen_token'
        self.config.codegen_org_id = 'valid_codegen_org_id'
        
        # Should now be valid
        errors = self.config.validate()
        self.assertEqual(len(errors), 0)


class TestGitHubManager(unittest.TestCase):
    """Test cases for the GitHubManager class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock configuration
        self.config = MagicMock()
        self.config.github_token = 'mock_github_token'
        self.config.repo_name = 'mock/repo'
        self.config.requirements_path = 'REQUIREMENTS.md'
        
        # Create mock Github client and repository
        self.mock_github = MagicMock()
        self.mock_repo = MagicMock()
        self.mock_github.get_repo.return_value = self.mock_repo
        
        # Patch the Github class
        self.github_patcher = patch('code_agent.core.workflow.Github', return_value=self.mock_github)
        self.mock_github_class = self.github_patcher.start()
        
        # Create the GitHubManager instance
        self.github_manager = GitHubManager(self.config)

    def tearDown(self):
        """Clean up after each test."""
        self.github_patcher.stop()

    def test_initialization(self):
        """Test that the GitHubManager initializes correctly."""
        # Check that the Github client was created with the token
        self.mock_github_class.assert_called_once_with('mock_github_token')
        
        # Check that the repo was retrieved
        self.mock_github.get_repo.assert_called_once_with('mock/repo')
        
        # Check that the manager has the correct attributes
        self.assertEqual(self.github_manager.config, self.config)
        self.assertEqual(self.github_manager.github_client, self.mock_github)
        self.assertEqual(self.github_manager.repo, self.mock_repo)

    def test_get_requirements(self):
        """Test fetching requirements from the repository."""
        # Mock the get_contents method
        mock_content_file = MagicMock()
        mock_content_file.decoded_content = b'# Requirements\n- Task 1\n- Task 2'
        self.mock_repo.get_contents.return_value = mock_content_file
        
        # Get requirements
        requirements = self.github_manager.get_requirements()
        
        # Check that get_contents was called with the correct path
        self.mock_repo.get_contents.assert_called_once_with('REQUIREMENTS.md')
        
        # Check that the requirements were decoded correctly
        self.assertEqual(requirements, '# Requirements\n- Task 1\n- Task 2')
        
        # Test error handling
        self.mock_repo.get_contents.side_effect = Exception("API error")
        requirements = self.github_manager.get_requirements()
        self.assertEqual(requirements, "")

    def test_create_branch(self):
        """Test creating a branch in the repository."""
        # Mock the get_git_ref and create_git_ref methods
        mock_ref = MagicMock()
        mock_ref.object.sha = 'base_commit_sha'
        self.mock_repo.get_git_ref.return_value = mock_ref
        
        # Create branch
        result = self.github_manager.create_branch('new-branch', 'main')
        
        # Check that the methods were called correctly
        self.mock_repo.get_git_ref.assert_called_once_with('heads/main')
        self.mock_repo.create_git_ref.assert_called_once_with(
            'refs/heads/new-branch', 'base_commit_sha'
        )
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling
        self.mock_repo.get_git_ref.side_effect = Exception("API error")
        result = self.github_manager.create_branch('error-branch', 'main')
        self.assertFalse(result)

    def test_create_pr(self):
        """Test creating a pull request in the repository."""
        # Mock the create_pull method
        mock_pr = MagicMock()
        mock_pr.number = 123
        self.mock_repo.create_pull.return_value = mock_pr
        
        # Create PR
        pr = self.github_manager.create_pr(
            title='Test PR',
            body='PR description',
            head='feature-branch',
            base='main'
        )
        
        # Check that create_pull was called with the correct arguments
        self.mock_repo.create_pull.assert_called_once_with(
            title='Test PR',
            body='PR description',
            head='feature-branch',
            base='main'
        )
        
        # Check that the PR was returned
        self.assertEqual(pr, mock_pr)
        
        # Test error handling
        self.mock_repo.create_pull.side_effect = Exception("API error")
        pr = self.github_manager.create_pr(
            title='Error PR',
            body='PR description',
            head='error-branch',
            base='main'
        )
        self.assertIsNone(pr)

    def test_get_pr(self):
        """Test getting a pull request by number."""
        # Mock the get_pull method
        mock_pr = MagicMock()
        mock_pr.number = 123
        self.mock_repo.get_pull.return_value = mock_pr
        
        # Get PR
        pr = self.github_manager.get_pr(123)
        
        # Check that get_pull was called with the correct number
        self.mock_repo.get_pull.assert_called_once_with(123)
        
        # Check that the PR was returned
        self.assertEqual(pr, mock_pr)
        
        # Test error handling
        self.mock_repo.get_pull.side_effect = Exception("API error")
        pr = self.github_manager.get_pr(456)
        self.assertIsNone(pr)

    def test_merge_pr(self):
        """Test merging a pull request."""
        # Mock the PR and its merge method
        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.merge.return_value = MagicMock()
        
        # Merge PR
        result = self.github_manager.merge_pr(mock_pr)
        
        # Check that merge was called with the correct method
        mock_pr.merge.assert_called_once_with(merge_method="squash")
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling
        mock_pr.merge.side_effect = Exception("API error")
        result = self.github_manager.merge_pr(mock_pr)
        self.assertFalse(result)

    def test_create_commit(self):
        """Test creating a commit with changes."""
        # Mock the necessary methods
        mock_ref = MagicMock()
        mock_commit = MagicMock()
        mock_commit.sha = 'commit_sha'
        mock_commit.commit.tree = MagicMock()
        
        self.mock_repo.get_git_ref.return_value = mock_ref
        self.mock_repo.get_commit.return_value = mock_commit
        self.mock_repo.create_git_blob.return_value = MagicMock(sha='blob_sha')
        self.mock_repo.create_git_tree.return_value = MagicMock(sha='tree_sha')
        self.mock_repo.get_git_commit.return_value = MagicMock()
        self.mock_repo.create_git_commit.return_value = MagicMock(sha='new_commit_sha')
        
        # Create commit
        result = self.github_manager.create_commit(
            branch='feature-branch',
            message='Test commit',
            changes={'file.py': 'print("Hello, World!")'}
        )
        
        # Check that the methods were called correctly
        self.mock_repo.get_git_ref.assert_called_once_with('heads/feature-branch')
        self.mock_repo.get_commit.assert_called_once()
        self.mock_repo.create_git_blob.assert_called_once_with('print("Hello, World!")', 'utf-8')
        self.mock_repo.create_git_tree.assert_called_once()
        self.mock_repo.get_git_commit.assert_called_once_with('commit_sha')
        self.mock_repo.create_git_commit.assert_called_once()
        mock_ref.edit.assert_called_once()
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling
        self.mock_repo.get_git_ref.side_effect = Exception("API error")
        result = self.github_manager.create_commit(
            branch='error-branch',
            message='Error commit',
            changes={'file.py': 'print("Error")'}
        )
        self.assertFalse(result)

    def test_update_requirements(self):
        """Test updating the requirements file."""
        # Mock the get_contents and update_file methods
        mock_content_file = MagicMock()
        mock_content_file.sha = 'file_sha'
        self.mock_repo.get_contents.return_value = mock_content_file
        
        # Update requirements
        result = self.github_manager.update_requirements('# Updated Requirements\n- Task 1 (done)\n- Task 2')
        
        # Check that the methods were called correctly
        self.mock_repo.get_contents.assert_called_once_with('REQUIREMENTS.md')
        self.mock_repo.update_file.assert_called_once_with(
            path='REQUIREMENTS.md',
            message='Update requirements progress [ci skip]',
            content='# Updated Requirements\n- Task 1 (done)\n- Task 2',
            sha='file_sha'
        )
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling
        self.mock_repo.get_contents.side_effect = Exception("API error")
        result = self.github_manager.update_requirements('# Error')
        self.assertFalse(result)

    def test_set_webhook(self):
        """Test setting a webhook on the repository."""
        # Mock the get_hooks and create_hook methods
        self.mock_repo.get_hooks.return_value = []
        
        # Set webhook
        result = self.github_manager.set_webhook('https://example.com/webhook')
        
        # Check that the methods were called correctly
        self.mock_repo.get_hooks.assert_called_once()
        self.mock_repo.create_hook.assert_called_once_with(
            name='web',
            config={
                'url': 'https://example.com/webhook',
                'content_type': 'json',
                'insecure_ssl': '0'
            },
            events=['pull_request'],
            active=True
        )
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test webhook already exists
        mock_hook = MagicMock()
        mock_hook.config = {'url': 'https://example.com/webhook'}
        self.mock_repo.get_hooks.return_value = [mock_hook]
        
        result = self.github_manager.set_webhook('https://example.com/webhook')
        
        # Should not create a new hook
        self.assertEqual(self.mock_repo.create_hook.call_count, 1)
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling
        self.mock_repo.get_hooks.side_effect = Exception("API error")
        result = self.github_manager.set_webhook('https://error.com/webhook')
        self.assertFalse(result)


class TestNgrokManager(unittest.TestCase):
    """Test cases for the NgrokManager class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock configuration
        self.config = MagicMock()
        self.config.ngrok_token = 'mock_ngrok_token'
        self.config.webhook_port = 5000
        self.config.webhook_path = '/webhook'
        
        # Patch the ngrok module
        self.ngrok_patcher = patch('code_agent.core.workflow.ngrok')
        self.mock_ngrok = self.ngrok_patcher.start()
        
        # Patch the conf module
        self.conf_patcher = patch('code_agent.core.workflow.conf')
        self.mock_conf = self.conf_patcher.start()
        self.mock_default_conf = MagicMock()
        self.mock_conf.get_default.return_value = self.mock_default_conf
        
        # Create the NgrokManager instance
        self.ngrok_manager = NgrokManager(self.config)

    def tearDown(self):
        """Clean up after each test."""
        self.ngrok_patcher.stop()
        self.conf_patcher.stop()

    def test_initialization(self):
        """Test that the NgrokManager initializes correctly."""
        # Check that the config was set
        self.assertEqual(self.ngrok_manager.config, self.config)
        
        # Check that the tunnel is None initially
        self.assertIsNone(self.ngrok_manager.tunnel)
        
        # Check that ngrok was configured with the token
        self.mock_conf.get_default.assert_called_once()
        self.assertEqual(self.mock_default_conf.auth_token, 'mock_ngrok_token')

    def test_start_tunnel(self):
        """Test starting an ngrok tunnel."""
        # Mock the connect method
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = 'https://example.ngrok.io'
        self.mock_ngrok.connect.return_value = mock_tunnel
        
        # Start tunnel
        url = self.ngrok_manager.start_tunnel()
        
        # Check that connect was called with the correct port
        self.mock_ngrok.connect.assert_called_once_with(5000, 'http')
        
        # Check that the tunnel was set
        self.assertEqual(self.ngrok_manager.tunnel, mock_tunnel)
        
        # Check that the webhook URL was set in the config
        self.assertEqual(self.config.webhook_url, 'https://example.ngrok.io/webhook')
        
        # Check that the URL was returned
        self.assertEqual(url, 'https://example.ngrok.io/webhook')
        
        # Test error handling
        self.mock_ngrok.connect.side_effect = Exception("ngrok error")
        url = self.ngrok_manager.start_tunnel()
        self.assertEqual(url, "")

    def test_stop_tunnel(self):
        """Test stopping the ngrok tunnel."""
        # Set a mock tunnel
        mock_tunnel = MagicMock()
        self.ngrok_manager.tunnel = mock_tunnel
        
        # Stop tunnel
        self.ngrok_manager.stop_tunnel()
        
        # Check that disconnect was called
        self.mock_ngrok.disconnect.assert_called_once_with(mock_tunnel.public_url)
        
        # Check that the tunnel was reset
        self.assertIsNone(self.ngrok_manager.tunnel)
        
        # Test when tunnel is None
        self.ngrok_manager.tunnel = None
        self.mock_ngrok.disconnect.reset_mock()
        
        self.ngrok_manager.stop_tunnel()
        
        # disconnect should not be called
        self.mock_ngrok.disconnect.assert_not_called()


# Mock classes for the remaining tests
@patch('code_agent.core.workflow.Agent')
class TestCodeGenManager(unittest.TestCase):
    """Test cases for the CodeGenManager class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock configuration
        self.config = MagicMock()
        self.config.codegen_token = 'mock_codegen_token'
        self.config.codegen_org_id = 'mock_codegen_org_id'

    def test_initialization(self, mock_agent_class):
        """Test that the CodeGenManager initializes correctly."""
        # Create the CodeGenManager instance
        codegen_manager = CodeGenManager(self.config)
        
        # Check that the Agent was created with the correct parameters
        mock_agent_class.assert_called_once_with(
            api_key='mock_codegen_token',
            org_id='mock_codegen_org_id'
        )
        
        # Check that the config was set
        self.assertEqual(codegen_manager.config, self.config)


class TestWorkflowManager(unittest.TestCase):
    """Test cases for the WorkflowManager class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock configuration
        self.config = MagicMock()
        
        # Patch the manager classes
        self.github_patcher = patch('code_agent.core.workflow.GitHubManager')
        self.ngrok_patcher = patch('code_agent.core.workflow.NgrokManager')
        self.codegen_patcher = patch('code_agent.core.workflow.CodeGenManager')
        self.deployment_patcher = patch('code_agent.core.workflow.DeploymentManager')
        self.webhook_patcher = patch('code_agent.core.workflow.WebhookServer')
        
        self.mock_github_manager = self.github_patcher.start()
        self.mock_ngrok_manager = self.ngrok_patcher.start()
        self.mock_codegen_manager = self.codegen_patcher.start()
        self.mock_deployment_manager = self.deployment_patcher.start()
        self.mock_webhook_server = self.webhook_patcher.start()
        
        # Create instances of the mocked managers
        self.mock_github_instance = MagicMock()
        self.mock_ngrok_instance = MagicMock()
        self.mock_codegen_instance = MagicMock()
        self.mock_deployment_instance = MagicMock()
        self.mock_webhook_instance = MagicMock()
        
        self.mock_github_manager.return_value = self.mock_github_instance
        self.mock_ngrok_manager.return_value = self.mock_ngrok_instance
        self.mock_codegen_manager.return_value = self.mock_codegen_instance
        self.mock_deployment_manager.return_value = self.mock_deployment_instance
        self.mock_webhook_server.return_value = self.mock_webhook_instance
        
        # Create the WorkflowManager instance
        self.workflow_manager = WorkflowManager(self.config)

    def tearDown(self):
        """Clean up after each test."""
        self.github_patcher.stop()
        self.ngrok_patcher.stop()
        self.codegen_patcher.stop()
        self.deployment_patcher.stop()
        self.webhook_patcher.stop()

    def test_initialization(self):
        """Test that the WorkflowManager initializes correctly."""
        # Check that the managers were created
        self.mock_github_manager.assert_called_once_with(self.config)
        self.mock_ngrok_manager.assert_called_once_with(self.config)
        self.mock_codegen_manager.assert_called_once_with(self.config)
        self.mock_deployment_manager.assert_called_once_with(self.config)
        
        # Check that the webhook server was not created yet
        self.mock_webhook_server.assert_not_called()
        
        # Check that the manager instances were set
        self.assertEqual(self.workflow_manager.github_manager, self.mock_github_instance)
        self.assertEqual(self.workflow_manager.ngrok_manager, self.mock_ngrok_instance)
        self.assertEqual(self.workflow_manager.codegen_manager, self.mock_codegen_instance)
        self.assertEqual(self.workflow_manager.deployment_manager, self.mock_deployment_instance)
        
        # Check that the webhook server is None initially
        self.assertIsNone(self.workflow_manager.webhook_server)

    def test_start(self):
        """Test starting the workflow."""
        # Mock the start_tunnel method to return a URL
        self.mock_ngrok_instance.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
        
        # Mock the set_webhook method to return True
        self.mock_github_instance.set_webhook.return_value = True
        
        # Start the workflow
        result = self.workflow_manager.start()
        
        # Check that the tunnel was started
        self.mock_ngrok_instance.start_tunnel.assert_called_once()
        
        # Check that the webhook was set
        self.mock_github_instance.set_webhook.assert_called_once_with('https://example.ngrok.io/webhook')
        
        # Check that the webhook server was created and started
        self.mock_webhook_server.assert_called_once_with(
            self.config, self.workflow_manager
        )
        self.mock_webhook_instance.start.assert_called_once()
        
        # Check that the result is True
        self.assertTrue(result)
        
        # Test error handling for tunnel start
        self.mock_ngrok_instance.start_tunnel.return_value = ""
        result = self.workflow_manager.start()
        self.assertFalse(result)
        
        # Reset for next test
        self.mock_ngrok_instance.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
        
        # Test error handling for webhook set
        self.mock_github_instance.set_webhook.return_value = False
        result = self.workflow_manager.start()
        self.assertFalse(result)

    def test_stop(self):
        """Test stopping the workflow."""
        # Set a mock webhook server
        self.workflow_manager.webhook_server = self.mock_webhook_instance
        
        # Stop the workflow
        self.workflow_manager.stop()
        
        # Check that the webhook server was stopped
        self.mock_webhook_instance.stop.assert_called_once()
        
        # Check that the tunnel was stopped
        self.mock_ngrok_instance.stop_tunnel.assert_called_once()
        
        # Test when webhook server is None
        self.workflow_manager.webhook_server = None
        self.mock_webhook_instance.stop.reset_mock()
        
        self.workflow_manager.stop()
        
        # stop should not be called on the webhook server
        self.mock_webhook_instance.stop.assert_not_called()
        
        # But the tunnel should still be stopped
        self.assertEqual(self.mock_ngrok_instance.stop_tunnel.call_count, 2)


if __name__ == '__main__':
    unittest.main()

