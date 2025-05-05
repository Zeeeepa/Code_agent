# Code Agent

An AI-powered code agent for GitHub repositories that helps automate development workflows.

## Features

- **Issue Solver**: Automatically analyze and solve GitHub issues
- **Context Manager**: Collect and manage context for AI-powered code generation
- **CI/CD Workflow**: Automate development workflows with GitHub and ngrok

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

## License

MIT
