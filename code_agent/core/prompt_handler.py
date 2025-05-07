#!/usr/bin/env python3
"""
Prompt Handler for Code Agent

This module provides functionality for handling prompt-based interactions
with the Codegen API, without requiring specific repository or issue selections.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .codegen_client import CodegenClient, TaskResult

# Set up logging
logger = logging.getLogger(__name__)

# Prompt templates for common use cases
PROMPT_TEMPLATES = {
    "code_explanation": (
        "Explain the following code in detail:\n"
        "```\n{code}\n```\n"
        "Focus on:\n"
        "- What the code does\n"
        "- Key functions and their purpose\n"
        "- Any potential issues or improvements"
    ),
    "bug_fix": (
        "Fix the following bug in my code:\n"
        "```\n{code}\n```\n"
        "Error message:\n"
        "```\n{error}\n```\n"
        "Please provide a working solution with an explanation of what was wrong."
    ),
    "feature_implementation": (
        "Implement the following feature:\n"
        "Feature description: {description}\n\n"
        "Context (existing code if applicable):\n"
        "```\n{context}\n```\n"
        "Please provide a complete implementation with explanations."
    ),
    "code_review": (
        "Review the following code and provide feedback:\n"
        "```\n{code}\n```\n"
        "Focus on:\n"
        "- Code quality and best practices\n"
        "- Potential bugs or edge cases\n"
        "- Performance considerations\n"
        "- Security issues"
    ),
    "refactoring": (
        "Refactor the following code to improve its quality:\n"
        "```\n{code}\n```\n"
        "Focus on:\n"
        "- Improving readability and maintainability\n"
        "- Reducing complexity\n"
        "- Applying design patterns where appropriate\n"
        "- Maintaining the same functionality"
    ),
    "custom": "{prompt}"
}

def get_template_placeholders(template_name: str) -> List[str]:
    """
    Get the placeholder variables for a given template.
    
    Args:
        template_name: The name of the template
        
    Returns:
        A list of placeholder names
    """
    if template_name not in PROMPT_TEMPLATES:
        return []
    
    template = PROMPT_TEMPLATES[template_name]
    # Find all placeholders in the format {placeholder}
    import re
    placeholders = re.findall(r'{(\w+)}', template)
    return placeholders

def fill_template(template_name: str, values: Dict[str, str]) -> str:
    """
    Fill a prompt template with the provided values.
    
    Args:
        template_name: The name of the template to use
        values: A dictionary of values to fill the template with
        
    Returns:
        The filled template
    """
    if template_name not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    
    template = PROMPT_TEMPLATES[template_name]
    
    # For custom template, just return the prompt
    if template_name == "custom":
        return values.get("prompt", "")
    
    # Check if all required placeholders are provided
    placeholders = get_template_placeholders(template_name)
    missing = [p for p in placeholders if p not in values]
    if missing:
        raise ValueError(f"Missing values for placeholders: {', '.join(missing)}")
    
    # Fill the template
    return template.format(**values)

def process_prompt(prompt: str, client: Optional[CodegenClient] = None) -> TaskResult:
    """
    Process a prompt using the Codegen API.
    
    Args:
        prompt: The prompt to process
        client: Optional CodegenClient instance. If not provided, a new one will be created.
        
    Returns:
        A TaskResult object containing the task status and result
    """
    # Create a client if not provided
    if client is None:
        api_key = os.environ.get("CODEGEN_TOKEN")
        org_id = os.environ.get("CODEGEN_ORG_ID")
        
        if not api_key or not org_id:
            raise ValueError(
                "Codegen API key and organization ID are required. "
                "Set the CODEGEN_TOKEN and CODEGEN_ORG_ID environment variables."
            )
        
        client = CodegenClient(api_key=api_key, org_id=org_id)
    
    # Run the task
    logger.info("Processing prompt with Codegen API")
    result = client.run_task(prompt=prompt, wait_for_completion=True)
    
    return result

def save_result(result: TaskResult, output_file: Optional[str] = None) -> None:
    """
    Save a task result to a file or print it to stdout.
    
    Args:
        result: The TaskResult to save
        output_file: Optional file path to save the result to. If not provided, print to stdout.
    """
    if output_file:
        with open(output_file, "w") as f:
            json.dump({
                "task_id": result.task_id,
                "status": result.status.value,
                "result": result.result,
                "error": result.error
            }, f, indent=2)
        logger.info(f"Result saved to {output_file}")
    else:
        print("\n" + "=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(f"Task ID: {result.task_id}")
        print(f"Status: {result.status.value}")
        
        if result.error:
            print(f"Error: {result.error}")
        
        if result.result:
            print("\n" + result.result)

