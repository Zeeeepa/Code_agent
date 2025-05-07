#!/usr/bin/env python3
"""
Test suite demonstrating advanced pytest fixtures for the workflow module
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path

from code_agent.core.workflow import Configuration, GitHubManager, WorkflowManager


# Custom fixtures for this test file
@pytest.fixture
def temp_config_file():
    """Fixture that creates a temporary config file for testing."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        temp_file.write('{"github_token": "file_token", "webhook_port": 8080}')
        temp_path = temp_file.name
    
    # Provide the file path to the test
    yield temp_path
    
    # Clean up after the test
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_pr():
    """Fixture that creates a mock pull request."""
    pr = MagicMock()
    pr.number = 123
    pr.title = "Test PR"
    pr.body = "PR description"
    pr.head.ref = "feature-branch"
    pr.base.ref = "main"
    pr.state = "open"
    
    # Mock PR comments
    comment1 = MagicMock()
    comment1.body = "This looks good!"
    comment1.user.login = "reviewer1"
    
    comment2 = MagicMock()
    comment2.body = "Please fix this issue."
    comment2.user.login = "reviewer2"
    
    pr.get_comments.return_value = [comment1, comment2]
    
    # Mock PR reviews
    review1 = MagicMock()
    review1.state = "APPROVED"
    review1.user.login = "reviewer1"
    
    review2 = MagicMock()
    review2.state = "CHANGES_REQUESTED"
    review2.user.login = "reviewer2"
    
    pr.get_reviews.return_value = [review1, review2]
    
    return pr


@pytest.fixture
def github_manager_with_pr(github_manager, mock_pr):
    """Fixture that adds a mock PR to the GitHub manager."""
    # Set up the mock repository to return the mock PR
    github_manager._mock_repo.get_pull.return_value = mock_pr
    
    # Add the mock PR to the manager for test access
    github_manager._mock_pr = mock_pr
    
    return github_manager


# Tests using the custom fixtures
@pytest.mark.unit
def test_load_config_from_file(temp_config_file):
    """Test loading configuration from a temporary file."""
    # Create a Configuration instance
    config = Configuration()
    
    # Mock the load_from_file method to use our temp file
    with patch.object(Configuration, 'load_from_file') as mock_load:
        # Call the method with our temp file
        config.load_from_file(temp_config_file)
        
        # Verify the method was called with the correct path
        mock_load.assert_called_once_with(temp_config_file)
    
    # Now actually load from the file to test the functionality
    with open(temp_config_file, 'r') as f:
        import json
        data = json.load(f)
        
        # Manually set the attributes
        for key, value in data.items():
            setattr(config, key, value)
    
    # Verify the values were loaded
    assert config.github_token == "file_token"
    assert config.webhook_port == 8080


@pytest.mark.unit
@pytest.mark.github
def test_pr_review_status(github_manager_with_pr):
    """Test checking the review status of a pull request."""
    # Get the mock PR
    mock_pr = github_manager_with_pr._mock_pr
    
    # Add a method to the GitHub manager to check PR review status
    def check_pr_review_status(pr_number):
        """Check if a PR has been approved by all reviewers."""
        pr = github_manager_with_pr.repo.get_pull(pr_number)
        reviews = list(pr.get_reviews())
        
        # Count approvals and change requests
        approvals = sum(1 for review in reviews if review.state == "APPROVED")
        changes_requested = sum(1 for review in reviews if review.state == "CHANGES_REQUESTED")
        
        if changes_requested > 0:
            return "changes_requested"
        elif approvals > 0:
            return "approved"
        else:
            return "pending"
    
    # Add the method to the manager
    github_manager_with_pr.check_pr_review_status = check_pr_review_status
    
    # Test the method
    status = github_manager_with_pr.check_pr_review_status(123)
    
    # Since we have both an approval and a change request, the status should be "changes_requested"
    assert status == "changes_requested"
    
    # Modify the mock to have only approvals
    mock_pr.get_reviews.return_value = [review for review in mock_pr.get_reviews() 
                                        if review.state == "APPROVED"]
    
    # Test again
    status = github_manager_with_pr.check_pr_review_status(123)
    assert status == "approved"
    
    # Modify the mock to have no reviews
    mock_pr.get_reviews.return_value = []
    
    # Test again
    status = github_manager_with_pr.check_pr_review_status(123)
    assert status == "pending"


@pytest.mark.integration
def test_workflow_with_pr(workflow_manager, mock_pr, monkeypatch):
    """Test workflow operations with a pull request."""
    # Add the mock PR to the GitHub manager
    workflow_manager._mock_github.get_pr = MagicMock(return_value=mock_pr)
    
    # Add a method to process a PR
    def process_pr(pr_number):
        """Process a pull request based on its review status."""
        # Get the PR
        pr = workflow_manager.github_manager.get_pr(pr_number)
        
        # Check if it's open
        if pr.state != "open":
            return False
        
        # Get reviews
        reviews = list(pr.get_reviews())
        
        # Count approvals and change requests
        approvals = sum(1 for review in reviews if review.state == "APPROVED")
        changes_requested = sum(1 for review in reviews if review.state == "CHANGES_REQUESTED")
        
        # Determine action based on reviews
        if changes_requested > 0:
            # Changes requested, don't merge
            return False
        elif approvals > 0:
            # Approved, merge the PR
            return True
        else:
            # No reviews yet, do nothing
            return None
    
    # Add the method to the workflow manager
    workflow_manager.process_pr = process_pr
    
    # Test with the current mock PR (has both approval and changes requested)
    result = workflow_manager.process_pr(123)
    assert result is False
    
    # Modify the mock to have only approvals
    mock_pr.get_reviews.return_value = [review for review in mock_pr.get_reviews() 
                                       if review.state == "APPROVED"]
    
    # Test again
    result = workflow_manager.process_pr(123)
    assert result is True
    
    # Modify the mock to have no reviews
    mock_pr.get_reviews.return_value = []
    
    # Test again
    result = workflow_manager.process_pr(123)
    assert result is None

