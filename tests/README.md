# Code Agent Tests

This directory contains tests for the Code Agent project.

## Running Tests

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
pytest tests/test_runner.py
```

To run a specific test function:

```bash
pytest tests/test_runner.py::TestRunner::test_issue_mode_success
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

- `conftest.py`: Contains pytest fixtures and configuration
- `test_installation.py`: Tests for verifying the installation
- `test_runner.py`: Tests for the runner module

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a new test file named `test_<module_name>.py`
2. Use pytest fixtures from `conftest.py` when possible
3. Mock external dependencies
4. Test both success and failure cases
5. Add docstrings to test classes and functions

