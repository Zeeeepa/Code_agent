# Code Agent

An AI-powered code agent for GitHub repositories that helps automate development workflows.

## Features

- **Prompt Mode**: Interact with Code Agent using natural language prompts
- **Issue Solver**: Automatically analyze and solve GitHub issues
- **Context Manager**: Collect and manage context for AI-powered code generation
- **CI/CD Workflow**: Automate development workflows with GitHub and ngrok
- **Robust Codegen Client**: Enhanced client for interacting with the Codegen API

## Installation

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/Code_agent.git
cd Code_agent

# Install the package
python install.py
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/Code_agent.git
cd Code_agent

# Install in development mode
python install.py --dev
# or
pip install -e .
```

### Using Make

The project includes a Makefile with several installation targets:

```bash
# Standard installation
make install

# Development installation
make install-dev

# Install and run tests
make install-test

# Install in development mode and run tests
make install-dev-test
```

## Usage

### Interactive Launcher

The easiest way to use Code Agent is with the interactive launcher:

```bash
# Run the interactive launcher
python start.py
```

This will present a menu with the following options:
1. **Prompt Mode** - Interact with Code Agent using natural language prompts
2. **Full Test Launch** - Run all tests to verify the installation
3. **Demo Launch** - Run the demo with a sample GitHub project
4. **Advanced Example** - Run with an actual GitHub project selected by the user

### Prompt Mode

The prompt mode allows you to interact with Code Agent using natural language prompts without requiring specific repository or issue selections.

```bash
# Run directly with a prompt
python -m code_agent.prompt_runner --prompt "Explain how to implement a binary search tree in Python"

# Use a template
python -m code_agent.prompt_runner --template code_explanation --code "def binary_search(arr, x): ..."

# Read prompt from a file
python -m code_agent.prompt_runner --file my_prompt.txt
```

Available templates:
- `code_explanation` - Explain code in detail
- `bug_fix` - Fix bugs in code
- `feature_implementation` - Implement a new feature
- `code_review` - Review code and provide feedback
- `refactoring` - Refactor code to improve quality
- `custom` - Use a custom prompt

### Command Line Interface

After installation, you can use the `code-agent` command. If the command is not found in your PATH, you can use the Python module directly:

```bash
# Show help
code-agent --help
# OR if command not found
python -m code_agent --help

# Run in issue mode
code-agent --mode issue --issue-number 123 --task-type bug
# OR
python -m code_agent --mode issue --issue-number 123 --task-type bug

# Run in context mode
code-agent --mode context collect --issue 123 --output context.json
# OR
python -m code_agent --mode context collect --issue 123 --output context.json

# Run in workflow mode
code-agent --mode workflow --repo-name owner/repo
# OR
python -m code_agent --mode workflow --repo-name owner/repo
```

### Troubleshooting CLI Command Not Found

If the `code-agent` command is not found after installation:

1. **Use the Python module directly**:
   ```bash
   python -m code_agent --help
   ```

2. **Find the CLI script location**:
   ```bash
   # On Linux/macOS
   find ~/.local/bin /usr/local/bin -name code-agent
   
   # On Windows
   where code-agent
   ```

3. **Add the directory to your PATH** if needed:
   ```bash
   # For Linux/macOS (add to ~/.bashrc or ~/.zshrc)
   export PATH=$PATH:~/.local/bin
   
   # For Windows (add to system environment variables)
   # Control Panel > System > Advanced System Settings > Environment Variables
   ```

4. **Use the local wrapper script** created during installation:
   ```bash
   # From the Code_agent directory
   ./code-agent --help
   ```

### Python Module

You can also use the package as a Python module:

```bash
# Show help
python -m code_agent --help

# Run the demo
python -m code_agent.demo --repo owner/repo --issue 123
```

### Demo

Run the demo script to see all components in action:

```bash
python -m code_agent.demo --repo <owner/repo> --issue <issue_number> --codegen-token <token> --codegen-org-id <org_id> --github-token <token>
```

## Project Structure

The project follows a standard Python package structure:

```
code_agent/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point for running as a module
├── runner.py           # Main runner script
├── demo.py             # Demo script
├── prompt_runner.py    # Prompt-based interaction runner
└── core/               # Core functionality
    ├── __init__.py
    ├── codegen_client.py  # Enhanced Codegen API client
    ├── config.py       # Configuration management
    ├── context_manager.py  # Context collection and management
    ├── integration.py  # Integration with external services
    ├── issue_solver.py # GitHub issue solver
    ├── prompt_handler.py # Prompt-based interaction handler
    └── workflow.py     # CI/CD workflow automation
```

## Testing

The project includes a comprehensive test suite:

```bash
# Run all tests
make test

# Run tests with coverage report
make test-coverage

# Run tests with HTML coverage report
make test-html

# Run tests for a specific module
make test-module MODULE=workflow
```

## Configuration

You can configure the tool using:

1. Environment variables
2. Command line arguments
3. Configuration file (code_agent_config.json)

Required environment variables:

- `GITHUB_TOKEN`: GitHub API token
- `CODEGEN_TOKEN`: CodeGen API token
- `CODEGEN_ORG_ID`: CodeGen organization ID
- `NGROK_TOKEN`: ngrok authentication token (for webhook exposure)

## Enhanced Codegen Client

The enhanced Codegen client (`code_agent.core.codegen_client.CodegenClient`) provides a robust interface for interacting with the Codegen API:

- **Improved Error Handling**: Robust exception handling with retries and exponential backoff
- **Asynchronous Processing**: Better polling mechanism with configurable intervals and timeouts
- **Enhanced Response Parsing**: Improved JSON parsing with support for various response formats
- **Type Safety**: Full type annotations for better IDE support and code quality
- **Comprehensive Logging**: Detailed logging of API interactions for debugging

Example usage:

```python
from code_agent.core.codegen_client import CodegenClient

# Initialize the client
client = CodegenClient(
    api_key="your-api-key",
    org_id="your-org-id"
)

# Run a task with a prompt
task_result = client.run_task(
    prompt="Your prompt here",
    wait_for_completion=True
)

# Check the result
if task_result.status.value == "completed":
    print(f"Task completed successfully: {task_result.result}")
else:
    print(f"Task failed: {task_result.error}")

# Parse JSON from the result
try:
    result_json = client.parse_json_result(task_result)
    print(f"Parsed JSON: {result_json}")
except ValueError as e:
    print(f"Failed to parse JSON: {e}")
```

## License

MIT
