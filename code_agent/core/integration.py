#!/usr/bin/env python3
"""
CodeGen Integration Helper

This module provides utility functions to help integrate the
three main components of the CodeGen system:
1. Issue Solver
2. Context Manager
3. CI/CD Workflow

It enables shared context and data passing between components.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

def extract_context_for_issue_solving(context_file: str, issue_number: int) -> Dict[str, Any]:
    """Extract relevant context from a context file for issue solving."""
    try:
        with open(context_file, 'r') as f:
            context_data = json.load(f)
        
        # Find the specific issue in the context
        issue_data = None
        for issue in context_data.get('issues', []):
            if issue.get('number') == issue_number:
                issue_data = issue
                break
        
        # Extract code snippets from relevant files based on issue context
        code_snippets = []
        if issue_data and context_data.get('files'):
            # Extract keywords from issue (simplified version)
            keywords = []
            if issue_data.get('title'):
                keywords.extend(issue_data['title'].split())
            if issue_data.get('body'):
                keywords.extend(issue_data['body'].split())
            
            # Filter keywords to be more specific (remove common words)
            keywords = [k.lower() for k in keywords if len(k) > 3]
            
            # Find relevant files based on keywords
            for file_path, file_info in context_data.get('files', {}).items():
                content = file_info.get('content', '')
                if any(kw in content.lower() for kw in keywords):
                    code_snippets.append({
                        'file': file_path,
                        'content': content
                    })
        
        return {
            'repository': context_data.get('repository', ''),
            'issue': issue_data or {},
            'code_snippets': code_snippets[:5],  # Limit to 5 most relevant files
            'error_logs': context_data.get('error_logs', [])
        }
    except Exception as e:
        print(f"Error extracting context for issue solving: {str(e)}")
        return {
            'repository': '',
            'issue': {},
            'code_snippets': [],
            'error_logs': []
        }

def prepare_workflow_from_issue_solution(task_id: str, context_file: str) -> Dict[str, Any]:
    """Prepare workflow context from an issue solution task."""
    try:
        # In a real implementation, you might query the CodeGen API to get the task result
        # For now, we'll create a placeholder
        workflow_context = {
            'task_id': task_id,
            'solution_type': 'issue',
            'source_context': context_file,
            'status': 'pending'
        }
        
        # Save the workflow context to a file
        workflow_file = f"workflow_context_{task_id}.json"
        with open(workflow_file, 'w') as f:
            json.dump(workflow_context, f, indent=2)
        
        return workflow_context
    except Exception as e:
        print(f"Error preparing workflow from issue solution: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'error',
            'error': str(e)
        }

def generate_requirements_from_context(context_file: str) -> str:
    """Generate a REQUIREMENTS.md file based on context."""
    try:
        with open(context_file, 'r') as f:
            context_data = json.load(f)
        
        # Extract issues and generate requirements
        issues = context_data.get('issues', [])
        
        requirements = "# Project Requirements\n\n"
        
        if issues:
            requirements += "## Issues to Resolve\n\n"
            for issue in issues:
                title = issue.get('title', 'Unknown Issue')
                number = issue.get('number', '???')
                requirements += f"- [ ] #{number}: {title}\n"
        
        # Add other sections based on repository analysis
        if context_data.get('codebase', {}).get('entry_points'):
            requirements += "\n## Code Structure\n\n"
            requirements += "Entry points:\n"
            for entry in context_data['codebase']['entry_points']:
                requirements += f"- {entry}\n"
        
        # Save the requirements file
        with open("REQUIREMENTS.md", 'w') as f:
            f.write(requirements)
        
        return requirements
    except Exception as e:
        print(f"Error generating requirements from context: {str(e)}")
        return "# Project Requirements\n\nError generating requirements."