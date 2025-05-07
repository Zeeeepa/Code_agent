#!/usr/bin/env python3
"""
Test suite demonstrating pytest's parametrize feature for the workflow module
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

from code_agent.core.workflow import Configuration


@pytest.mark.unit
@pytest.mark.parametrize("env_vars,expected_values", [
    # Test case 1: All environment variables set
    (
        {
            'GITHUB_TOKEN': 'env_github_token',
            'NGROK_TOKEN': 'env_ngrok_token',
            'REPO_NAME': 'env/repo',
            'CODEGEN_TOKEN': 'env_codegen_token',
            'CODEGEN_ORG_ID': 'env_codegen_org_id'
        },
        {
            'github_token': 'env_github_token',
            'ngrok_token': 'env_ngrok_token',
            'repo_name': 'env/repo',
            'codegen_token': 'env_codegen_token',
            'codegen_org_id': 'env_codegen_org_id'
        }
    ),
    # Test case 2: Only some environment variables set
    (
        {
            'GITHUB_TOKEN': 'partial_github_token',
            'REPO_NAME': 'partial/repo'
        },
        {
            'github_token': 'partial_github_token',
            'ngrok_token': '',
            'repo_name': 'partial/repo',
            'codegen_token': '',
            'codegen_org_id': ''
        }
    ),
    # Test case 3: No environment variables set
    (
        {},
        {
            'github_token': '',
            'ngrok_token': '',
            'repo_name': '',
            'codegen_token': '',
            'codegen_org_id': ''
        }
    )
])
def test_load_from_env_parametrized(env_vars, expected_values, clean_env):
    """Test loading configuration from environment variables with different scenarios."""
    # Set environment variables for this test case
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Create and load config
    config = Configuration()
    config.load_from_env()
    
    # Check that values were loaded correctly
    for attr, expected in expected_values.items():
        assert getattr(config, attr) == expected


@pytest.mark.unit
@pytest.mark.parametrize("input_config,expected_errors", [
    # Test case 1: All required values missing
    (
        {},
        ["GitHub token is not provided", "ngrok token is not provided", 
         "Repository name is not provided", "CodeGen token is not provided", 
         "CodeGen organization ID is not provided"]
    ),
    # Test case 2: Some required values missing
    (
        {'github_token': 'token', 'repo_name': 'repo'},
        ["ngrok token is not provided", "CodeGen token is not provided", 
         "CodeGen organization ID is not provided"]
    ),
    # Test case 3: All required values present
    (
        {'github_token': 'token', 'ngrok_token': 'token', 'repo_name': 'repo',
         'codegen_token': 'token', 'codegen_org_id': 'id'},
        []
    )
])
def test_validate_parametrized(input_config, expected_errors):
    """Test configuration validation with different scenarios."""
    # Create config and set attributes
    config = Configuration()
    for attr, value in input_config.items():
        setattr(config, attr, value)
    
    # Validate and check errors
    errors = config.validate()
    assert len(errors) == len(expected_errors)
    for error in expected_errors:
        assert error in errors


@pytest.mark.unit
@pytest.mark.parametrize("webhook_url,expected_result", [
    # Test case 1: Valid webhook URL
    ('https://example.com/webhook', True),
    # Test case 2: Empty webhook URL
    ('', False)
])
def test_set_webhook(webhook_url, expected_result, github_manager):
    """Test setting a webhook with different URLs."""
    # Set up the mock repository
    mock_repo = github_manager._mock_repo
    
    # Mock the create_hook method based on the expected result
    if expected_result:
        mock_hook = MagicMock()
        mock_repo.create_hook.return_value = mock_hook
    else:
        mock_repo.create_hook.side_effect = Exception("Invalid URL")
    
    # Set the webhook
    result = github_manager.set_webhook(webhook_url)
    
    # Check the result
    assert result is expected_result
    
    # If we expected success, verify the hook was created correctly
    if expected_result:
        mock_repo.create_hook.assert_called_once()
        # Verify the hook configuration
        call_args = mock_repo.create_hook.call_args[1]
        assert call_args['name'] == 'web'
        assert call_args['config']['url'] == webhook_url
        assert call_args['config']['content_type'] == 'json'
        assert call_args['events'] == ['push', 'pull_request']
        assert call_args['active'] is True

