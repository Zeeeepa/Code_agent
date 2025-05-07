# Code Agent

An AI-powered code agent for GitHub repositories that helps automate development workflows.

## Features

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

### Command Line Interface

After installation, you can use the `code-agent` command:

```bash
# Show help
code-agent --help

# Run in issue mode
code-agent --mode issue --issue-number 123 --task-type bug

# Run in context mode
code-agent --mode context collect --issue 123 --output context.json

# Run in workflow mode
code-agent --mode workflow --repo-name owner/repo
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
└── core/               # Core functionality
    ├── __init__.py
    ├── codegen_client.py  # Enhanced Codegen API client
    ├── config.py       # Configuration management
    ├── context_manager.py  # Context collection and management
    ├── integration.py  # Integration with external services
    ├── issue_solver.py # GitHub issue solver
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
- **Circuit Breaker Pattern**: Protection against repeated calls to failing services
- **Request Validation**: Pre-request validation to catch common errors
- **Flexible Configuration**: Support for environment variables and runtime configuration
- **Rate Limiting Handling**: Smart retry logic with exponential backoff and jitter
- **PR Review Functionality**: Support for different review types with line-by-line comments

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

### PR Review Functionality

The client includes support for reviewing GitHub pull requests with different review types:

```python
# Review a pull request
review_result = client.review_pull_request(
    repo_owner="owner",
    repo_name="repo",
    pr_number=123,
    review_command="/gemini-review",
    github_token="your-github-token"
)

# Post comments to a PR
client.post_pr_comments(
    repo_owner="owner",
    repo_name="repo",
    pr_number=123,
    comments=["Comment 1", "Comment 2"],
    github_token="your-github-token"
)
```

Supported review commands:
- `/review` - Standard code review
- `/gemini-review` - Thorough code review with security focus
- `/korbit-review` - Security-focused code review
- `/improve` - Suggestions for code improvements

### Configuration Options

The client can be configured through constructor arguments or environment variables:

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `api_key` | `CODEGEN_TOKEN` or `CODEGEN_API_KEY` | Codegen API key |
| `org_id` | `CODEGEN_ORG_ID` or `CODEGEN_ORGANIZATION_ID` | Codegen organization ID |
| `max_retries` | `CODEGEN_MAX_RETRIES` | Maximum number of retries for API calls |
| `retry_delay` | `CODEGEN_RETRY_DELAY` | Initial delay between retries (seconds) |
| `polling_interval` | `CODEGEN_POLLING_INTERVAL` | Interval between polling for task status (seconds) |
| `polling_timeout` | `CODEGEN_POLLING_TIMEOUT` | Maximum time to wait for task completion (seconds) |
| `request_timeout` | `CODEGEN_REQUEST_TIMEOUT` | Timeout for individual API requests (seconds) |
| `circuit_breaker_threshold` | `CODEGEN_CIRCUIT_BREAKER_THRESHOLD` | Number of failures before opening circuit |
| `circuit_breaker_recovery_time` | `CODEGEN_CIRCUIT_BREAKER_RECOVERY_TIME` | Time to wait before recovery attempt (seconds) |
