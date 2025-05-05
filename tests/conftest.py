#!/usr/bin/env python3
"""
Pytest configuration file for Code Agent tests
"""

import os
import sys
import pytest

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

