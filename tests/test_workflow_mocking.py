#!/usr/bin/env python3
"""
Test suite demonstrating advanced pytest mocking for the workflow module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call

from code_agent.core.workflow import (
    Configuration, 
    GitHubManager, 
    NgrokManager, 
    CodeGenManager, 
    WorkflowManager
)


@pytest.mark.unit
def test_github_webhook_creation(github_manager):
    """Test creating a GitHub webhook with detailed mocking."""
    # Set up the mock repository
    mock_repo = github_manager._mock_repo
    
    # Create a more detailed mock for the hook
    mock_hook = MagicMock()
    mock_hook.id = 12345
    mock_hook.config = {
        'url': 'https://example.com/webhook',
        'content_type': 'json',
        'insecure_ssl': '0'
    }
    mock_hook.events = ['push', 'pull_request']
    mock_hook.active = True
    
    # Set up the mock to return our detailed hook
    mock_repo.create_hook.return_value = mock_hook
    
    # Call the method
    result = github_manager.set_webhook('https://example.com/webhook')
    
    # Verify the result
    assert result is True
    
    # Verify the hook was created with the correct parameters
    mock_repo.create_hook.assert_called_once()
    call_args = mock_repo.create_hook.call_args[1]
    assert call_args['name'] == 'web'
    assert call_args['config']['url'] == 'https://example.com/webhook'
    assert call_args['config']['content_type'] == 'json'
    assert call_args['events'] == ['push', 'pull_request']
    assert call_args['active'] is True


@pytest.mark.unit
def test_ngrok_tunnel_lifecycle(ngrok_manager):
    """Test the complete lifecycle of an ngrok tunnel with detailed mocking."""
    # Set up the mock ngrok module
    mock_ngrok = ngrok_manager._mock_ngrok
    
    # Create a more detailed mock for the tunnel
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = 'https://example.ngrok.io'
    mock_tunnel.proto = 'https'
    mock_tunnel.metrics = {
        'http': {
            'count': 10,
            'rate': 1.5
        }
    }
    
    # Set up the mock to return our detailed tunnel
    mock_ngrok.connect.return_value = mock_tunnel
    
    # Start the tunnel
    url = ngrok_manager.start_tunnel()
    
    # Verify the result
    assert url == 'https://example.ngrok.io/webhook'
    
    # Verify the tunnel was created with the correct parameters
    mock_ngrok.connect.assert_called_once_with(5000, 'http')
    
    # Verify the tunnel was set
    assert ngrok_manager.tunnel == mock_tunnel
    
    # Verify the webhook URL was set in the config
    assert ngrok_manager.config.webhook_url == 'https://example.ngrok.io/webhook'
    
    # Now stop the tunnel
    ngrok_manager.stop_tunnel()
    
    # Verify disconnect was called with the correct URL
    mock_ngrok.disconnect.assert_called_once_with('https://example.ngrok.io')
    
    # Verify the tunnel was reset
    assert ngrok_manager.tunnel is None


@pytest.mark.unit
def test_codegen_api_interaction(codegen_manager, monkeypatch):
    """Test interactions with the CodeGen API with detailed mocking."""
    # Get the mock agent
    mock_agent = codegen_manager._mock_agent
    
    # Create a mock response for the agent
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 'task-123',
        'status': 'completed',
        'result': {
            'code': 'def hello_world():\n    print("Hello, World!")',
            'explanation': 'This is a simple hello world function.'
        }
    }
    
    # Set up the mock agent to return our response
    mock_agent.generate_code.return_value = mock_response
    
    # Add a method to the CodeGen manager to generate code
    def generate_hello_world():
        """Generate a hello world function using the CodeGen API."""
        response = self.agent.generate_code(
            prompt="Write a hello world function in Python",
            language="python"
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['result']['code']
        else:
            return None
    
    # Add the method to the manager
    codegen_manager.generate_hello_world = generate_hello_world.__get__(codegen_manager)
    
    # Call the method
    code = codegen_manager.generate_hello_world()
    
    # Verify the result
    assert code == 'def hello_world():\n    print("Hello, World!")'
    
    # Verify the agent was called with the correct parameters
    mock_agent.generate_code.assert_called_once()
    call_args = mock_agent.generate_code.call_args[1]
    assert call_args['prompt'] == "Write a hello world function in Python"
    assert call_args['language'] == "python"


@pytest.mark.integration
def test_workflow_webhook_handling(workflow_manager, monkeypatch):
    """Test handling webhook events in the workflow manager."""
    # Create a mock webhook event
    webhook_event = {
        'action': 'opened',
        'pull_request': {
            'number': 123,
            'title': 'Test PR',
            'body': 'This is a test PR',
            'head': {
                'ref': 'feature-branch'
            },
            'base': {
                'ref': 'main'
            }
        },
        'repository': {
            'full_name': 'mock/repo'
        }
    }
    
    # Create a mock webhook handler
    def handle_webhook_event(event):
        """Handle a webhook event."""
        # Check if it's a PR event
        if 'pull_request' in event:
            pr = event['pull_request']
            
            # Get the PR number
            pr_number = pr['number']
            
            # Get the PR from GitHub
            github_pr = self.github_manager.get_pr(pr_number)
            
            # Process based on the action
            if event['action'] == 'opened':
                # New PR opened, add a comment
                self.github_manager.add_pr_comment(
                    pr_number, 
                    "Thanks for opening this PR! I'll review it shortly."
                )
                return True
            elif event['action'] == 'closed':
                # PR closed, clean up
                return True
        
        # Not a PR event or not handled
        return False
    
    # Add the method to the workflow manager
    workflow_manager.handle_webhook_event = handle_webhook_event.__get__(workflow_manager)
    
    # Mock the GitHub manager's get_pr and add_pr_comment methods
    workflow_manager._mock_github.get_pr = MagicMock()
    workflow_manager._mock_github.add_pr_comment = MagicMock()
    
    # Call the method
    result = workflow_manager.handle_webhook_event(webhook_event)
    
    # Verify the result
    assert result is True
    
    # Verify the GitHub manager methods were called correctly
    workflow_manager._mock_github.get_pr.assert_called_once_with(123)
    workflow_manager._mock_github.add_pr_comment.assert_called_once_with(
        123, 
        "Thanks for opening this PR! I'll review it shortly."
    )
    
    # Test with a different action
    webhook_event['action'] = 'closed'
    workflow_manager._mock_github.get_pr.reset_mock()
    workflow_manager._mock_github.add_pr_comment.reset_mock()
    
    result = workflow_manager.handle_webhook_event(webhook_event)
    
    # Verify the result
    assert result is True
    
    # Verify get_pr was called but add_pr_comment was not
    workflow_manager._mock_github.get_pr.assert_called_once_with(123)
    workflow_manager._mock_github.add_pr_comment.assert_not_called()
    
    # Test with a non-PR event
    non_pr_event = {
        'action': 'pushed',
        'repository': {
            'full_name': 'mock/repo'
        }
    }
    
    workflow_manager._mock_github.get_pr.reset_mock()
    
    result = workflow_manager.handle_webhook_event(non_pr_event)
    
    # Verify the result
    assert result is False
    
    # Verify no GitHub manager methods were called
    workflow_manager._mock_github.get_pr.assert_not_called()

