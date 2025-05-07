#!/usr/bin/env python3
"""
Pytest configuration file for Code Agent tests
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow importing the code_agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define fixtures that can be reused across test files
@pytest.fixture
def mock_issue_args():
    """Fixture for issue mode arguments"""
    from argparse import Namespace
    return Namespace(
        mode='issue',
        issue_number=123,
        task_type='bug',
        org_id='test-org-id',
        token='test-token'
    )

@pytest.fixture
def mock_context_args():
    """Fixture for context mode arguments"""
    from argparse import Namespace
    return Namespace(
        mode='context',
        command='collect',
        output='context.json',
        issue=None,
        pr=None,
        max_files=20,
        file_patterns=None,
        exclude_patterns=None
    )

@pytest.fixture
def mock_workflow_args():
    """Fixture for workflow mode arguments"""
    from argparse import Namespace
    return Namespace(
        mode='workflow',
        github_token='github-token',
        ngrok_token='ngrok-token',
        repo_name='owner/repo',
        codegen_token='codegen-token',
        codegen_org_id='codegen-org-id',
        webhook_port=5000
    )

# Workflow module fixtures
@pytest.fixture
def mock_config():
    """Fixture for Configuration class"""
    from code_agent.core.workflow import Configuration
    config = Configuration()
    config.github_token = 'mock_github_token'
    config.ngrok_token = 'mock_ngrok_token'
    config.repo_name = 'mock/repo'
    config.codegen_token = 'mock_codegen_token'
    config.codegen_org_id = 'mock_codegen_org_id'
    config.webhook_port = 5000
    config.webhook_path = '/webhook'
    config.requirements_path = 'REQUIREMENTS.md'
    config.deployment_script_path = 'deploy.py'
    return config

@pytest.fixture
def mock_github_repo():
    """Fixture for mocked GitHub repository"""
    mock_repo = MagicMock()
    mock_repo.get_contents.return_value.decoded_content = b'# Requirements\n- Task 1\n- Task 2'
    
    # Mock reference for branch creation
    mock_ref = MagicMock()
    mock_ref.object.sha = 'base_commit_sha'
    mock_repo.get_git_ref.return_value = mock_ref
    
    # Mock PR creation
    mock_pr = MagicMock()
    mock_pr.number = 123
    mock_repo.create_pull.return_value = mock_pr
    
    return mock_repo

@pytest.fixture
def mock_github_client(mock_github_repo):
    """Fixture for mocked GitHub client"""
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_github_repo
    return mock_github

@pytest.fixture
def github_manager(mock_config, monkeypatch):
    """Fixture for GitHubManager with mocked dependencies"""
    from code_agent.core.workflow import GitHubManager
    
    # Create a mock Github client
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo
    
    # Patch the Github class
    monkeypatch.setattr('code_agent.core.workflow.Github', lambda token: mock_github)
    
    # Create and return the manager
    manager = GitHubManager(mock_config)
    
    # Add the mocks as attributes for test access
    manager._mock_github = mock_github
    manager._mock_repo = mock_repo
    
    return manager

@pytest.fixture
def ngrok_manager(mock_config, monkeypatch):
    """Fixture for NgrokManager with mocked dependencies"""
    from code_agent.core.workflow import NgrokManager
    
    # Mock the ngrok module
    mock_ngrok = MagicMock()
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = 'https://example.ngrok.io'
    mock_ngrok.connect.return_value = mock_tunnel
    
    # Mock the conf module
    mock_conf = MagicMock()
    mock_default_conf = MagicMock()
    mock_conf.get_default.return_value = mock_default_conf
    
    # Patch the modules
    monkeypatch.setattr('code_agent.core.workflow.ngrok', mock_ngrok)
    monkeypatch.setattr('code_agent.core.workflow.conf', mock_conf)
    
    # Create and return the manager
    manager = NgrokManager(mock_config)
    
    # Add the mocks as attributes for test access
    manager._mock_ngrok = mock_ngrok
    manager._mock_conf = mock_conf
    manager._mock_tunnel = mock_tunnel
    
    return manager

@pytest.fixture
def codegen_manager(mock_config, monkeypatch):
    """Fixture for CodeGenManager with mocked dependencies"""
    from code_agent.core.workflow import CodeGenManager
    
    # Mock the Agent class
    mock_agent = MagicMock()
    mock_agent_class = MagicMock(return_value=mock_agent)
    
    # Patch the Agent class
    monkeypatch.setattr('code_agent.core.workflow.Agent', mock_agent_class)
    
    # Create and return the manager
    manager = CodeGenManager(mock_config)
    
    # Add the mocks as attributes for test access
    manager._mock_agent = mock_agent
    manager._mock_agent_class = mock_agent_class
    
    return manager

@pytest.fixture
def workflow_manager(mock_config, monkeypatch):
    """Fixture for WorkflowManager with mocked dependencies"""
    from code_agent.core.workflow import WorkflowManager, GitHubManager, NgrokManager, CodeGenManager, DeploymentManager, WebhookServer
    
    # Create mock instances
    mock_github = MagicMock()
    mock_ngrok = MagicMock()
    mock_codegen = MagicMock()
    mock_deployment = MagicMock()
    mock_webhook = MagicMock()
    
    # Set up the ngrok tunnel URL
    mock_ngrok.start_tunnel.return_value = 'https://example.ngrok.io/webhook'
    
    # Set up the GitHub webhook
    mock_github.set_webhook.return_value = True
    
    # Patch the manager classes
    monkeypatch.setattr('code_agent.core.workflow.GitHubManager', lambda config: mock_github)
    monkeypatch.setattr('code_agent.core.workflow.NgrokManager', lambda config: mock_ngrok)
    monkeypatch.setattr('code_agent.core.workflow.CodeGenManager', lambda config: mock_codegen)
    monkeypatch.setattr('code_agent.core.workflow.DeploymentManager', lambda config: mock_deployment)
    monkeypatch.setattr('code_agent.core.workflow.WebhookServer', lambda config, workflow_manager: mock_webhook)
    
    # Create and return the manager
    manager = WorkflowManager(mock_config)
    
    # Add the mocks as attributes for test access
    manager._mock_github = mock_github
    manager._mock_ngrok = mock_ngrok
    manager._mock_codegen = mock_codegen
    manager._mock_deployment = mock_deployment
    manager._mock_webhook = mock_webhook
    
    return manager

@pytest.fixture
def clean_env():
    """Fixture to provide a clean environment for tests that modify environment variables"""
    # Save original environment
    original_env = os.environ.copy()
    
    # Clear relevant environment variables
    for var in ['GITHUB_TOKEN', 'NGROK_TOKEN', 'REPO_NAME', 
                'CODEGEN_TOKEN', 'CODEGEN_ORG_ID']:
        if var in os.environ:
            del os.environ[var]
    
    # Provide the test with a clean environment
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
