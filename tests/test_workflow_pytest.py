#!/usr/bin/env python3
"""
Test suite for the Code Agent Workflow Manager using pytest
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import threading
import time
from pathlib import Path

# Import the workflow module components
from code_agent.core.workflow import (
    Configuration, 
    GitHubManager, 
    NgrokManager, 
    CodeGenManager, 
    DeploymentManager, 
    WebhookServer, 
    WorkflowManager
)


# Configuration Tests
@pytest.mark.unit
class TestConfiguration:
    """Test cases for the Configuration class."""

    def test_default_initialization(self):
        """Test that the config initializes with default values."""
        config = Configuration()
        
        # Check default values
        assert config.github_token == ""
        assert config.ngrok_token == ""
        assert config.repo_name == ""
        assert config.codegen_token == ""
        assert config.codegen_org_id == ""
        assert config.webhook_url == ""
        assert config.webhook_port == 5000
        assert config.webhook_path == "/webhook"
        assert config.requirements_path == "REQUIREMENTS.md"
        assert config.test_branch_prefix == "test-"
        assert config.deployment_script_path == "deploy.py"

    def test_load_from_env(self, clean_env):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ['GITHUB_TOKEN'] = 'test_github_token'
        os.environ['NGROK_TOKEN'] = 'test_ngrok_token'
        os.environ['REPO_NAME'] = 'test/repo'
        os.environ['CODEGEN_TOKEN'] = 'test_codegen_token'
        os.environ['CODEGEN_ORG_ID'] = 'test_codegen_org_id'
        
        # Load from environment
        config = Configuration()
        config.load_from_env()
        
        # Check that values were loaded from environment
        assert config.github_token == 'test_github_token'
        assert config.ngrok_token == 'test_ngrok_token'
        assert config.repo_name == 'test/repo'
        assert config.codegen_token == 'test_codegen_token'
        assert config.codegen_org_id == 'test_codegen_org_id'

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
        config = Configuration()
        config.load_from_args(args)
        
        # Check that values were loaded from args
        assert config.github_token == 'args_github_token'
        assert config.ngrok_token == 'args_ngrok_token'
        assert config.repo_name == 'args/repo'
        assert config.codegen_token == 'args_codegen_token'
        assert config.codegen_org_id == 'args_codegen_org_id'
        assert config.webhook_port == 8080

    def test_validate(self):
        """Test configuration validation."""
        # Empty config should have validation errors
        config = Configuration()
        errors = config.validate()
        assert len(errors) == 5
        assert "GitHub token is not provided" in errors
        assert "ngrok token is not provided" in errors
        assert "Repository name is not provided" in errors
        assert "CodeGen token is not provided" in errors
        assert "CodeGen organization ID is not provided" in errors
        
        # Set required values
        config.github_token = 'valid_github_token'
        config.ngrok_token = 'valid_ngrok_token'
        config.repo_name = 'valid/repo'
        config.codegen_token = 'valid_codegen_token'
        config.codegen_org_id = 'valid_codegen_org_id'
        
        # Should now be valid
        errors = config.validate()
        assert len(errors) == 0


# GitHub Manager Tests
@pytest.mark.unit
@pytest.mark.github
class TestGitHubManager:
    """Test cases for the GitHubManager class."""

    def test_initialization(self, github_manager, mock_config):
        """Test that the GitHubManager initializes correctly."""
        # Check that the manager has the correct attributes
        assert github_manager.config == mock_config
        assert github_manager._mock_github.get_repo.called

    def test_get_requirements(self, github_manager):
        """Test fetching requirements from the repository."""
        # Set up the mock repository
        mock_repo = github_manager._mock_repo
        mock_content_file = MagicMock()
        mock_content_file.decoded_content = b'# Requirements\n- Task 1\n- Task 2'
        mock_repo.get_contents.return_value = mock_content_file
        
        # Get requirements
        requirements = github_manager.get_requirements()
        
        # Check that get_contents was called with the correct path
        mock_repo.get_contents.assert_called_once_with('REQUIREMENTS.md')
        
        # Check that the requirements were decoded correctly
        assert requirements == '# Requirements\n- Task 1\n- Task 2'
        
        # Test error handling
        mock_repo.get_contents.side_effect = Exception("API error")
        requirements = github_manager.get_requirements()
        assert requirements == ""

    def test_create_branch(self, github_manager):
        """Test creating a branch in the repository."""
        # Set up the mock repository
        mock_repo = github_manager._mock_repo
        mock_ref = MagicMock()
        mock_ref.object.sha = 'base_commit_sha'
        mock_repo.get_git_ref.return_value = mock_ref
        
        # Create branch
        result = github_manager.create_branch('new-branch', 'main')
        
        # Check that the methods were called correctly
        mock_repo.get_git_ref.assert_called_once_with('heads/main')
        mock_repo.create_git_ref.assert_called_once_with(
            'refs/heads/new-branch', 'base_commit_sha'
        )
        
        # Check that the result is True
        assert result is True
        
        # Test error handling
        mock_repo.get_git_ref.side_effect = Exception("API error")
        result = github_manager.create_branch('error-branch', 'main')
        assert result is False

    def test_create_pr(self, github_manager):
        """Test creating a pull request in the repository."""
        # Set up the mock repository
        mock_repo = github_manager._mock_repo
        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_repo.create_pull.return_value = mock_pr
        
        # Create PR
        pr = github_manager.create_pr(
            title='Test PR',
            body='PR description',
            head='feature-branch',
            base='main'
        )
        
        # Check that create_pull was called with the correct arguments
        mock_repo.create_pull.assert_called_once_with(
            title='Test PR',
            body='PR description',
            head='feature-branch',
            base='main'
        )
        
        # Check that the PR was returned
        assert pr == mock_pr
        
        # Test error handling
        mock_repo.create_pull.side_effect = Exception("API error")
        pr = github_manager.create_pr(
            title='Error PR',
            body='PR description',
            head='error-branch',
            base='main'
        )
        assert pr is None


# Ngrok Manager Tests
@pytest.mark.unit
@pytest.mark.ngrok
class TestNgrokManager:
    """Test cases for the NgrokManager class."""

    def test_initialization(self, ngrok_manager, mock_config):
        """Test that the NgrokManager initializes correctly."""
        # Check that the config was set
        assert ngrok_manager.config == mock_config
        
        # Check that the tunnel is None initially
        assert ngrok_manager.tunnel is None
        
        # Check that ngrok was configured with the token
        ngrok_manager._mock_conf.get_default.assert_called_once()
        assert ngrok_manager._mock_conf.get_default().auth_token == 'mock_ngrok_token'

    def test_start_tunnel(self, ngrok_manager):
        """Test starting an ngrok tunnel."""
        # Set up the mock tunnel
        mock_ngrok = ngrok_manager._mock_ngrok
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = 'https://example.ngrok.io'
        mock_ngrok.connect.return_value = mock_tunnel
        
        # Start tunnel
        url = ngrok_manager.start_tunnel()
        
        # Check that connect was called with the correct port
        mock_ngrok.connect.assert_called_once_with(5000, 'http')
        
        # Check that the tunnel was set
        assert ngrok_manager.tunnel == mock_tunnel
        
        # Check that the webhook URL was set in the config
        assert ngrok_manager.config.webhook_url == 'https://example.ngrok.io/webhook'
        
        # Check that the URL was returned
        assert url == 'https://example.ngrok.io/webhook'
        
        # Test error handling
        mock_ngrok.connect.side_effect = Exception("ngrok error")
        url = ngrok_manager.start_tunnel()
        assert url == ""

    def test_stop_tunnel(self):
        """Test stopping the ngrok tunnel."""
        # Create a mock configuration
        config = MagicMock()
        
        # Create a mock ngrok module
        mock_ngrok = MagicMock()
        
        # Create a mock tunnel
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = 'https://example.ngrok.io'
        
        # Patch the ngrok module
        with patch('code_agent.core.workflow.ngrok', mock_ngrok):
            # Create the NgrokManager instance
            manager = NgrokManager(config)
            
            # Set the tunnel
            manager.tunnel = mock_tunnel
            
            # Stop tunnel
            manager.stop_tunnel()
            
            # Check that disconnect was called
            mock_ngrok.disconnect.assert_called_once_with('https://example.ngrok.io')
            
            # Check that the tunnel was reset
            assert manager.tunnel is None
            
            # Test when tunnel is None
            manager.tunnel = None
            mock_ngrok.disconnect.reset_mock()
            
            manager.stop_tunnel()
            
            # disconnect should not be called
            mock_ngrok.disconnect.assert_not_called()


# CodeGen Manager Tests
@pytest.mark.unit
@pytest.mark.codegen
class TestCodeGenManager:
    """Test cases for the CodeGenManager class."""

    def test_initialization(self, mock_config):
        """Test that the CodeGenManager initializes correctly."""
        # Create a mock Agent class
        with patch('code_agent.core.workflow.Agent') as mock_agent_class:
            # Create a new manager
            manager = CodeGenManager(mock_config)
            
            # Check that the Agent was created with the correct parameters
            mock_agent_class.assert_called_once_with(
                token='mock_codegen_token',
                org_id='mock_codegen_org_id'
            )
            
            # Check that the config was set
            assert manager.config == mock_config


# Workflow Manager Tests
@pytest.mark.unit
class TestWorkflowManager:
    """Test cases for the WorkflowManager class."""

    def test_initialization(self):
        """Test that the WorkflowManager initializes correctly."""
        # Create a mock configuration
        config = MagicMock()
        
        # Create mock managers
        mock_github = MagicMock()
        mock_ngrok = MagicMock()
        mock_codegen = MagicMock()
        mock_deployment = MagicMock()
        mock_webhook = MagicMock()
        
        # Patch the manager classes
        with patch('code_agent.core.workflow.GitHubManager', return_value=mock_github) as mock_github_class, \
             patch('code_agent.core.workflow.NgrokManager', return_value=mock_ngrok) as mock_ngrok_class, \
             patch('code_agent.core.workflow.CodeGenManager', return_value=mock_codegen) as mock_codegen_class, \
             patch('code_agent.core.workflow.DeploymentManager') as mock_deployment_class, \
             patch('code_agent.core.workflow.WebhookServer', return_value=mock_webhook) as mock_webhook_class:
            
            # Create the WorkflowManager instance
            manager = WorkflowManager(config)
            
            # Check that the manager classes were called with the correct arguments
            mock_github_class.assert_called_once_with(config)
            mock_ngrok_class.assert_called_once_with(config)
            mock_codegen_class.assert_called_once_with(config)
            mock_deployment_class.assert_called_once_with(config, mock_github)
            mock_webhook_class.assert_called_once_with(config, manager)
            
            # Check that the manager instances were set
            assert manager.github_manager == mock_github
            assert manager.ngrok_manager == mock_ngrok
            assert manager.codegen_manager == mock_codegen
            assert manager.webhook_server == mock_webhook
            
            # Check that the running flag is False initially
            assert manager.running is False

    def test_start(self):
        """Test starting the workflow."""
        # Create a configuration
        config = Configuration()
        config.github_token = 'test_token'
        config.ngrok_token = 'test_token'
        config.repo_name = 'test/repo'
        config.codegen_token = 'test_token'
        config.codegen_org_id = 'test_id'
        
        # Create mock managers and webhook server
        mock_github = MagicMock()
        mock_ngrok = MagicMock()
        mock_codegen = MagicMock()
        mock_deployment = MagicMock()
        mock_webhook = MagicMock()
        
        # Set up the ngrok tunnel URL
        mock_ngrok.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
        
        # Set up the GitHub webhook
        mock_github.set_webhook.return_value = True
        
        # Create a partial WorkflowManager with mocked dependencies
        with patch.object(WorkflowManager, '__init__', return_value=None):
            manager = WorkflowManager()
            manager.config = config
            manager.github_manager = mock_github
            manager.ngrok_manager = mock_ngrok
            manager.codegen_manager = mock_codegen
            manager.deployment_manager = mock_deployment
            manager.webhook_server = mock_webhook
            manager.running = False
            
            # Start the workflow
            result = manager.start()
            
            # Check that the tunnel was started
            mock_ngrok.start_tunnel.assert_called_once()
            
            # Check that the webhook was set
            mock_github.set_webhook.assert_called_once_with('https://example.ngrok.io/webhook')
            
            # Check that the webhook server was started
            mock_webhook.start.assert_called_once()
            
            # Check that the result is True
            assert result is True
            
            # Test error handling for tunnel start
            mock_ngrok.start_tunnel.return_value = ""
            result = manager.start()
            assert result is False
            
            # Reset for next test
            mock_ngrok.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
            
            # Test error handling for webhook set
            mock_github.set_webhook.return_value = False
            result = manager.start()
            assert result is False

    def test_stop(self):
        """Test stopping the workflow."""
        # Create a configuration
        config = Configuration()
        
        # Create mock managers and webhook server
        mock_github = MagicMock()
        mock_ngrok = MagicMock()
        mock_codegen = MagicMock()
        mock_deployment = MagicMock()
        mock_webhook = MagicMock()
        
        # Create a partial WorkflowManager with mocked dependencies
        with patch.object(WorkflowManager, '__init__', return_value=None):
            manager = WorkflowManager()
            manager.config = config
            manager.github_manager = mock_github
            manager.ngrok_manager = mock_ngrok
            manager.codegen_manager = mock_codegen
            manager.deployment_manager = mock_deployment
            manager.webhook_server = mock_webhook
            manager.running = True
            
            # Stop the workflow
            manager.stop()
            
            # Check that the webhook server was stopped
            mock_webhook.stop.assert_called_once()
            
            # Check that the tunnel was stopped
            mock_ngrok.stop_tunnel.assert_called_once()


# Integration tests that combine multiple components
@pytest.mark.integration
def test_workflow_end_to_end():
    """Test the entire workflow process from start to finish."""
    # Create a configuration
    config = Configuration()
    config.github_token = 'test_token'
    config.ngrok_token = 'test_token'
    config.repo_name = 'test/repo'
    config.codegen_token = 'test_token'
    config.codegen_org_id = 'test_id'
    
    # Create mock managers and webhook server
    mock_github = MagicMock()
    mock_ngrok = MagicMock()
    mock_codegen = MagicMock()
    mock_deployment = MagicMock()
    mock_webhook = MagicMock()
    
    # Set up the ngrok tunnel URL
    mock_ngrok.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
    
    # Set up the GitHub webhook
    mock_github.set_webhook.return_value = True
    
    # Create a partial WorkflowManager with mocked dependencies
    with patch.object(WorkflowManager, '__init__', return_value=None):
        workflow_manager = WorkflowManager()
        workflow_manager.config = config
        workflow_manager.github_manager = mock_github
        workflow_manager.ngrok_manager = mock_ngrok
        workflow_manager.codegen_manager = mock_codegen
        workflow_manager.deployment_manager = mock_deployment
        workflow_manager.webhook_server = mock_webhook
        workflow_manager.running = False
        
        # Start the workflow
        result = workflow_manager.start()
        assert result is True
        
        # Verify that the components were initialized and started correctly
        mock_ngrok.start_tunnel.assert_called_once()
        mock_github.set_webhook.assert_called_once_with('https://example.ngrok.io/webhook')
        mock_webhook.start.assert_called_once()
        
        # Stop the workflow
        workflow_manager.stop()
        
        # Verify that the components were stopped correctly
        mock_webhook.stop.assert_called_once()
        mock_ngrok.stop_tunnel.assert_called_once()
