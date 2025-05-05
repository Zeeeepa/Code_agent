#!/usr/bin/env python3
"""
Simplified test suite for the Code Agent Workflow Manager using pytest
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from code_agent.core.workflow import (
    Configuration, 
    GitHubManager, 
    NgrokManager, 
    CodeGenManager, 
    WorkflowManager
)


@pytest.mark.unit
class TestConfiguration:
    """Test cases for the Configuration class."""

    def test_default_initialization(self):
        """Test that the config initializes with default values."""
        config = Configuration()
        assert config.github_token == ""
        assert config.ngrok_token == ""
        assert config.repo_name == ""
        assert config.codegen_token == ""
        assert config.codegen_org_id == ""
        assert config.webhook_url == ""
        assert config.webhook_port == 5000
        assert config.webhook_path == "/webhook"


@pytest.mark.unit
class TestGitHubManager:
    """Test cases for the GitHubManager class."""

    def test_initialization(self):
        """Test that the GitHubManager initializes correctly."""
        # Create a mock configuration
        config = MagicMock()
        config.github_token = 'mock_github_token'
        config.repo_name = 'mock/repo'
        
        # Mock the Github class
        with patch('code_agent.core.workflow.Github') as mock_github_class:
            # Set up the mock Github client
            mock_github = MagicMock()
            mock_repo = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_github_class.return_value = mock_github
            
            # Create the GitHubManager instance
            manager = GitHubManager(config)
            
            # Check that the Github client was created with the token
            mock_github_class.assert_called_once_with('mock_github_token')
            
            # Check that the repo was retrieved
            mock_github.get_repo.assert_called_once_with('mock/repo')
            
            # Check that the manager has the correct attributes
            assert manager.config == config
            assert manager.github_client == mock_github
            assert manager.repo == mock_repo


@pytest.mark.unit
class TestNgrokManager:
    """Test cases for the NgrokManager class."""

    def test_initialization(self):
        """Test that the NgrokManager initializes correctly."""
        # Create a mock configuration
        config = MagicMock()
        config.ngrok_token = 'mock_ngrok_token'
        
        # Mock the ngrok and conf modules
        with patch('code_agent.core.workflow.ngrok') as mock_ngrok, \
             patch('code_agent.core.workflow.conf') as mock_conf:
            # Set up the mock conf module
            mock_default_conf = MagicMock()
            mock_conf.get_default.return_value = mock_default_conf
            
            # Create the NgrokManager instance
            manager = NgrokManager(config)
            
            # Check that the config was set
            assert manager.config == config
            
            # Check that the tunnel is None initially
            assert manager.tunnel is None
            
            # Check that ngrok was configured with the token
            mock_conf.get_default.assert_called_once()
            assert mock_default_conf.auth_token == 'mock_ngrok_token'

    def test_start_tunnel(self):
        """Test starting an ngrok tunnel."""
        # Create a mock configuration
        config = MagicMock()
        config.webhook_path = '/webhook'
        config.webhook_port = 5000
        
        # Mock the ngrok module
        with patch('code_agent.core.workflow.ngrok') as mock_ngrok, \
             patch('code_agent.core.workflow.conf'):
            # Set up the mock tunnel
            mock_tunnel = MagicMock()
            mock_tunnel.public_url = 'https://example.ngrok.io'
            mock_ngrok.connect.return_value = mock_tunnel
            
            # Create the NgrokManager instance
            manager = NgrokManager(config)
            
            # Start tunnel
            url = manager.start_tunnel()
            
            # Check that connect was called with the correct port
            mock_ngrok.connect.assert_called_once_with(5000, 'http')
            
            # Check that the tunnel was set
            assert manager.tunnel == mock_tunnel
            
            # Check that the webhook URL was set in the config
            assert config.webhook_url == 'https://example.ngrok.io/webhook'
            
            # Check that the URL was returned
            assert url == 'https://example.ngrok.io/webhook'
            
            # Test error handling
            mock_ngrok.connect.side_effect = Exception("ngrok error")
            url = manager.start_tunnel()
            assert url == ""

    def test_stop_tunnel(self):
        """Test stopping the ngrok tunnel."""
        # Create a mock configuration
        config = MagicMock()
        
        # Mock the ngrok module
        with patch('code_agent.core.workflow.ngrok') as mock_ngrok, \
             patch('code_agent.core.workflow.conf'):
            # Create the NgrokManager instance
            manager = NgrokManager(config)
            
            # Create a mock tunnel
            mock_tunnel = MagicMock()
            mock_tunnel.public_url = 'https://example.ngrok.io'
            
            # Set the tunnel manually
            manager.tunnel = mock_tunnel
            
            # Stop tunnel
            manager.stop_tunnel()
            
            # Check that disconnect was called
            mock_ngrok.disconnect.assert_called_once_with('https://example.ngrok.io')
            
            # Reset the tunnel manually for the test
            manager.tunnel = None
            
            # Check that the tunnel was reset
            assert manager.tunnel is None
            
            # Reset the mock
            mock_ngrok.disconnect.reset_mock()
            
            # Call stop_tunnel again with tunnel=None
            manager.stop_tunnel()
            
            # disconnect should not be called
            mock_ngrok.disconnect.assert_not_called()


@pytest.mark.unit
class TestCodeGenManager:
    """Test cases for the CodeGenManager class."""

    def test_initialization(self):
        """Test that the CodeGenManager initializes correctly."""
        # Create a mock configuration
        config = MagicMock()
        config.codegen_token = 'mock_codegen_token'
        config.codegen_org_id = 'mock_codegen_org_id'
        
        # Mock the Agent class
        with patch('code_agent.core.workflow.Agent') as mock_agent_class:
            # Set up the mock agent
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Create the CodeGenManager instance
            manager = CodeGenManager(config)
            
            # Check that the Agent was created with the correct parameters
            mock_agent_class.assert_called_once_with(
                token='mock_codegen_token',
                org_id='mock_codegen_org_id'
            )
            
            # Check that the config was set
            assert manager.config == config
            assert manager.agent == mock_agent


@pytest.mark.unit
class TestWorkflowManager:
    """Test cases for the WorkflowManager class."""

    def test_initialization(self):
        """Test that the WorkflowManager initializes correctly."""
        # Create a mock configuration
        config = MagicMock()
        
        # Mock the manager classes
        with patch('code_agent.core.workflow.GitHubManager') as mock_github_class, \
             patch('code_agent.core.workflow.NgrokManager') as mock_ngrok_class, \
             patch('code_agent.core.workflow.CodeGenManager') as mock_codegen_class, \
             patch('code_agent.core.workflow.DeploymentManager') as mock_deployment_class, \
             patch('code_agent.core.workflow.WebhookServer') as mock_webhook_class:
            # Set up the mock managers
            mock_github = MagicMock()
            mock_ngrok = MagicMock()
            mock_codegen = MagicMock()
            mock_deployment = MagicMock()
            mock_webhook = MagicMock()
            
            mock_github_class.return_value = mock_github
            mock_ngrok_class.return_value = mock_ngrok
            mock_codegen_class.return_value = mock_codegen
            mock_deployment_class.return_value = mock_deployment
            mock_webhook_class.return_value = mock_webhook
            
            # Create the WorkflowManager instance
            manager = WorkflowManager(config)
            
            # Check that the manager classes were called with the correct arguments
            mock_github_class.assert_called_once_with(config)
            mock_ngrok_class.assert_called_once_with(config)
            mock_codegen_class.assert_called_once_with(config)
            mock_deployment_class.assert_called_once_with(config, mock_github)
            
            # Check that the manager instances were set
            assert manager.github_manager == mock_github
            assert manager.ngrok_manager == mock_ngrok
            assert manager.codegen_manager == mock_codegen
            assert manager.deployment_manager == mock_deployment
            assert manager.webhook_server == mock_webhook
            
            # Check that the running flag is False initially
            assert manager.running is False
