#!/usr/bin/env python3
"""
Test suite for the Code Agent Configuration Manager
"""

import os
import sys
import json
import unittest
import tempfile
import argparse
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code_agent.core.config import CodeAgentConfig, get_config, init_config_from_args


class TestCodeAgentConfig(unittest.TestCase):
    """Test cases for the CodeAgentConfig class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a fresh config instance for each test
        self.config = CodeAgentConfig()
        
        # Save original environment variables to restore later
        self.original_env = os.environ.copy()
        
        # Clear relevant environment variables for testing
        for var in ['CODEGEN_TOKEN', 'CODEGEN_ORG_ID', 'GITHUB_TOKEN', 
                    'GITHUB_REPOSITORY', 'NGROK_TOKEN']:
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up after each test."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_initialization(self):
        """Test that the config initializes with default values."""
        config = CodeAgentConfig()
        
        # Check default values
        self.assertEqual(config.codegen_token, "")
        self.assertEqual(config.codegen_org_id, "")
        self.assertEqual(config.github_token, "")
        self.assertEqual(config.repo_name, "")
        self.assertEqual(config.ngrok_token, "")
        self.assertEqual(config.webhook_port, 5000)
        self.assertEqual(config.webhook_path, "/webhook")
        self.assertEqual(config.requirements_path, "REQUIREMENTS.md")
        self.assertEqual(config.deployment_script_path, "deploy.py")
        self.assertEqual(config.context_output_path, "context.json")

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ['CODEGEN_TOKEN'] = 'test_token'
        os.environ['CODEGEN_ORG_ID'] = 'test_org_id'
        os.environ['GITHUB_TOKEN'] = 'test_github_token'
        os.environ['GITHUB_REPOSITORY'] = 'test/repo'
        os.environ['NGROK_TOKEN'] = 'test_ngrok_token'
        
        # Create a new config instance to load from environment
        config = CodeAgentConfig()
        
        # Check that values were loaded from environment
        self.assertEqual(config.codegen_token, 'test_token')
        self.assertEqual(config.codegen_org_id, 'test_org_id')
        self.assertEqual(config.github_token, 'test_github_token')
        self.assertEqual(config.repo_name, 'test/repo')
        self.assertEqual(config.ngrok_token, 'test_ngrok_token')

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"codegen_token": "file_token", "webhook_port": 8080}')
    def test_load_from_file(self, mock_file, mock_exists):
        """Test loading configuration from a JSON file."""
        # Mock that the file exists
        mock_exists.return_value = True
        
        # Create a new config instance with mocked file
        config = CodeAgentConfig()
        
        # Check that values were loaded from file
        self.assertEqual(config.codegen_token, 'file_token')
        self.assertEqual(config.webhook_port, 8080)
        
        # Verify the file was opened
        mock_file.assert_called_with(Path('code_agent_config.json'), 'r')

    def test_update_from_args(self):
        """Test updating configuration from command line arguments."""
        # Create args namespace
        args = argparse.Namespace(
            codegen_token='args_token',
            github_token='args_github_token',
            webhook_port=9000,
            nonexistent_attr='should_be_ignored'
        )
        
        # Update config from args
        self.config.update_from_args(args)
        
        # Check that values were updated
        self.assertEqual(self.config.codegen_token, 'args_token')
        self.assertEqual(self.config.github_token, 'args_github_token')
        self.assertEqual(self.config.webhook_port, 9000)
        
        # Check that non-existent attributes were not added
        self.assertFalse(hasattr(self.config, 'nonexistent_attr'))

    def test_save_to_file(self):
        """Test saving configuration to a JSON file."""
        # Set some config values
        self.config.codegen_token = 'save_token'
        self.config.webhook_port = 7000
        
        # Use a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Save config to the temporary file
            result = self.config.save_to_file(temp_path)
            self.assertTrue(result)
            
            # Read the file and check its contents
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            self.assertEqual(saved_data['codegen_token'], 'save_token')
            self.assertEqual(saved_data['webhook_port'], 7000)
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_validate(self):
        """Test configuration validation."""
        # Empty config should have validation errors
        errors = self.config.validate()
        self.assertEqual(len(errors), 2)
        self.assertIn("CodeGen API token (codegen_token) is not set", errors)
        self.assertIn("CodeGen organization ID (codegen_org_id) is not set", errors)
        
        # Set required values
        self.config.codegen_token = 'valid_token'
        self.config.codegen_org_id = 'valid_org_id'
        
        # Should now be valid
        errors = self.config.validate()
        self.assertEqual(len(errors), 0)

    def test_get_as_dict(self):
        """Test getting configuration as a dictionary."""
        # Set some values
        self.config.codegen_token = 'dict_token'
        self.config.webhook_port = 6000
        
        # Get as dict
        config_dict = self.config.get_as_dict()
        
        # Check dict contents
        self.assertEqual(config_dict['codegen_token'], 'dict_token')
        self.assertEqual(config_dict['webhook_port'], 6000)
        
        # Check that private attributes are not included
        self.config._private_attr = 'private'
        config_dict = self.config.get_as_dict()
        self.assertNotIn('_private_attr', config_dict)

    def test_get_config(self):
        """Test the get_config singleton function."""
        # Get the singleton instance
        singleton = get_config()
        
        # Should be the same instance as the global config
        from code_agent.core.config import config
        self.assertIs(singleton, config)

    def test_init_config_from_args(self):
        """Test initializing config from args."""
        # Create args namespace
        args = argparse.Namespace(
            codegen_token='init_token',
            webhook_port=4000
        )
        
        # Get reference to the singleton before modification
        from code_agent.core.config import config as global_config
        
        # Initialize config from args
        result = init_config_from_args(args)
        
        # Check that values were updated in the singleton
        self.assertEqual(global_config.codegen_token, 'init_token')
        self.assertEqual(global_config.webhook_port, 4000)
        
        # Should return the singleton
        self.assertIs(result, global_config)


if __name__ == '__main__':
    unittest.main()
