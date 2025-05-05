# Code Agent Tests

This directory contains tests for the Code Agent project.

## Running Tests

### Using the Test Runner Script

The easiest way to run tests is using the test runner script:

```bash
python run_tests.py
```

This script provides several options:

```bash
python run_tests.py --help  # Show all available options
python run_tests.py -m workflow  # Run only workflow tests
python run_tests.py -c  # Generate coverage report
python run_tests.py -H  # Generate HTML coverage report
python run_tests.py -v  # Run with verbose output
```

### Using pytest directly

To run all tests:

```bash
pytest
```

To run tests with verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_workflow.py
```

To run tests with a specific marker:

```bash
pytest -m unit  # Run unit tests
pytest -m integration  # Run integration tests
pytest -m github  # Run GitHub-related tests
```

To run tests with coverage:

```bash
pytest --cov=code_agent
```

To generate an HTML coverage report:

```bash
pytest --cov=code_agent --cov-report=html
```

## Test Coverage

To generate a test coverage report, install pytest-cov:

```bash
pip install pytest-cov
```

Then run:

```bash
pytest --cov=code_agent
```

For a detailed HTML report:

```bash
pytest --cov=code_agent --cov-report=html
```

## Test Structure

The tests are organized using pytest, a powerful testing framework for Python. The test structure includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **Parametrized Tests**: Test multiple scenarios with different inputs
- **Fixtures**: Reusable test components and setup/teardown

### Test Files

- `conftest.py`: Contains pytest fixtures and configuration
- `test_installation.py`: Tests for verifying the installation
- `test_runner.py`: Tests for the runner module
- `test_workflow.py`: Tests for the workflow module (unittest style)
- `test_workflow_pytest.py`: Tests for the workflow module (pytest style)
- `test_workflow_parametrized.py`: Demonstrates pytest's parametrize feature
- `test_workflow_fixtures.py`: Demonstrates advanced pytest fixtures
- `test_workflow_mocking.py`: Demonstrates advanced pytest mocking
- `test_integration.py`: Tests for the integration module
- `test_issue_solver.py`: Tests for the issue solver module
- `test_config.py`: Tests for the configuration module

### Pytest Markers

The tests use the following markers to categorize them:

- `unit`: Unit tests that test individual components
- `integration`: Integration tests that test interactions between components
- `github`: Tests that interact with the GitHub API
- `ngrok`: Tests that interact with ngrok
- `codegen`: Tests that interact with the CodeGen API
- `slow`: Slow running tests

You can run tests with a specific marker using:

```bash
pytest -m marker_name
```

### Fixtures

The tests use fixtures defined in `conftest.py` to set up test environments and provide mock objects. Some key fixtures include:

- `mock_config`: Provides a pre-configured Configuration instance
- `github_manager`: Provides a GitHubManager with mocked dependencies
- `ngrok_manager`: Provides an NgrokManager with mocked dependencies
- `codegen_manager`: Provides a CodeGenManager with mocked dependencies
- `workflow_manager`: Provides a WorkflowManager with mocked dependencies
- `clean_env`: Provides a clean environment for tests that modify environment variables

## Adding New Tests

When adding new tests, follow these guidelines:

1. Use pytest style tests with fixtures and markers
2. Add appropriate markers to categorize your tests
3. Mock external dependencies
4. Test both success and failure cases
5. Add docstrings to test classes and functions
6. Use parametrize for testing multiple scenarios
7. Use fixtures for common setup and teardown
