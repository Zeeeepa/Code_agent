#!/usr/bin/env python3
"""
Code Agent Configuration Manager

This module provides centralized configuration management for all Code Agent components:
- Issue Solver
- Context Manager
- CI/CD Workflow

Configuration can be loaded from:
1. Environment variables
2. Configuration file (code_agent_config.json)
3. Command line arguments
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

class CodeAgentConfig:
    """Manages configuration for all Code Agent components."""
    
    def __init__(self):
        """Initialize the configuration with default values."""
        # Core CodeGen settings
        self.codegen_token = ""
        self.codegen_org_id = ""
        
        # GitHub settings
        self.github_token = ""
        self.repo_name = ""
        
        # Webhook and ngrok settings
        self.ngrok_token = ""
        self.webhook_port = 5000
        self.webhook_path = "/webhook"
        
        # File paths
        self.requirements_path = "REQUIREMENTS.md"
        self.deployment_script_path = "deploy.py"
        self.context_output_path = "context.json"
        
        # Load configuration from all sources
        self._load_from_env()
        self._load_from_file()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # CodeGen settings
        self.codegen_token = os.environ.get("CODEGEN_TOKEN", self.codegen_token)
        self.codegen_org_id = os.environ.get("CODEGEN_ORG_ID", self.codegen_org_id)
        
        # GitHub settings
        self.github_token = os.environ.get("GITHUB_TOKEN", self.github_token)
        self.repo_name = os.environ.get("GITHUB_REPOSITORY", self.repo_name)
        
        # Webhook and ngrok settings
        self.ngrok_token = os.environ.get("NGROK_TOKEN", self.ngrok_token)
    
    def _load_from_file(self, config_path: str = "code_agent_config.json"):
        """Load configuration from a JSON file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update attributes from config file
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except Exception as e:
            print(f"Warning: Failed to load configuration from {config_path}: {str(e)}")
    
    def update_from_args(self, args: argparse.Namespace):
        """Update configuration from command line arguments."""
        # Update attributes from args
        for key, value in vars(args).items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
    
    def save_to_file(self, config_path: str = "code_agent_config.json"):
        """Save current configuration to a JSON file."""
        try:
            config_data = {key: value for key, value in self.__dict__.items() 
                          if not key.startswith('_')}
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
            return False
    
    def validate(self) -> list:
        """Validate the configuration and return a list of errors."""
        errors = []
        
        # Validate based on which components are being used
        # For now, just check the core CodeGen settings
        if not self.codegen_token:
            errors.append("CodeGen API token (codegen_token) is not set")
        if not self.codegen_org_id:
            errors.append("CodeGen organization ID (codegen_org_id) is not set")
        
        return errors
    
    def get_as_dict(self) -> Dict[str, Any]:
        """Get the configuration as a dictionary."""
        return {key: value for key, value in self.__dict__.items() 
                if not key.startswith('_')}

# Singleton instance for easy access across modules
config = CodeAgentConfig()

def get_config() -> CodeAgentConfig:
    """Get the singleton configuration instance."""
    return config

def init_config_from_args(args: argparse.Namespace) -> CodeAgentConfig:
    """Initialize configuration from command line arguments."""
    config.update_from_args(args)
    return config
