#!/usr/bin/env python3
"""
Code Agent Prompt Runner

This script provides a command-line interface for running prompts with Code Agent.
It allows users to interact with the Codegen API using natural language prompts
without requiring specific repository or issue selections.

Usage:
    python -m code_agent.prompt_runner --prompt "Your prompt here"
    python -m code_agent.prompt_runner --template code_explanation --code "def hello(): print('world')"
    python -m code_agent.prompt_runner --file prompt.txt
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from code_agent.core.prompt_handler import (
    PROMPT_TEMPLATES, 
    get_template_placeholders, 
    fill_template, 
    process_prompt, 
    save_result
)
from code_agent.core.codegen_client import CodegenClient

def main():
    parser = argparse.ArgumentParser(description="Code Agent Prompt Runner")
    
    # Template or prompt options (mutually exclusive)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Direct prompt to send to Codegen API")
    prompt_group.add_argument("--template", choices=list(PROMPT_TEMPLATES.keys()), 
                             help="Prompt template to use")
    prompt_group.add_argument("--file", help="File containing the prompt")
    
    # Template placeholder values
    for template_name in PROMPT_TEMPLATES:
        placeholders = get_template_placeholders(template_name)
        for placeholder in placeholders:
            parser.add_argument(f"--{placeholder}", help=f"Value for {placeholder} in template")
    
    # Output options
    parser.add_argument("--output", "-o", help="Output file for the result")
    
    # API credentials
    parser.add_argument("--codegen-token", help="Codegen API token")
    parser.add_argument("--codegen-org-id", help="Codegen organization ID")
    
    args = parser.parse_args()
    
    # Get the prompt
    prompt = None
    
    if args.prompt:
        prompt = args.prompt
    elif args.file:
        with open(args.file, "r") as f:
            prompt = f.read()
    elif args.template:
        # Get values for template placeholders
        values = {}
        placeholders = get_template_placeholders(args.template)
        
        for placeholder in placeholders:
            value = getattr(args, placeholder, None)
            if value is None:
                print(f"Error: Missing value for placeholder '{placeholder}' in template '{args.template}'")
                print(f"Please provide it with --{placeholder}")
                sys.exit(1)
            values[placeholder] = value
        
        prompt = fill_template(args.template, values)
    
    # Initialize the client
    api_key = args.codegen_token or os.environ.get("CODEGEN_TOKEN")
    org_id = args.codegen_org_id or os.environ.get("CODEGEN_ORG_ID")
    
    if not api_key or not org_id:
        print("Error: Codegen API key and organization ID are required.")
        print("Provide them as arguments or set CODEGEN_TOKEN and CODEGEN_ORG_ID environment variables.")
        sys.exit(1)
    
    client = CodegenClient(api_key=api_key, org_id=org_id)
    
    # Process the prompt
    try:
        print("Processing prompt with Codegen API...")
        result = process_prompt(prompt, client=client)
        
        # Save or display the result
        save_result(result, args.output)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

