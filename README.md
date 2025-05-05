# Code Agent

An AI-powered code agent for GitHub repositories that helps automate development workflows.

## Features

- **Issue Solver**: Automatically analyze and solve GitHub issues
- **Context Manager**: Collect and manage context for AI-powered code generation
- **CI/CD Workflow**: Automate development workflows with GitHub and ngrok

## Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/Code_agent.git
cd Code_agent

# Option 1: Quick install
pip install -r requirements.txt
pip install -e .

# Option 2: Use the installation script
python install.py --dev
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

## Development

To run tests:

```bash
python tests/test_installation.py
```

## License

MIT

