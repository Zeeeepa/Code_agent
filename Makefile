.PHONY: test test-coverage test-html clean install install-dev

# Default target
all: test

# Install the package
install:
	python setup.py

# Install development dependencies
install-dev:
	python setup.py --dev

# Run tests after installation
install-test:
	python setup.py --test

# Install in development mode and run tests
install-dev-test:
	python setup.py --dev --test

# Run all tests
test:
	python run_tests.py -v

# Run tests with coverage report
test-coverage:
	python run_tests.py -c -v

# Run tests with HTML coverage report
test-html:
	python run_tests.py -H -v

# Run specific module tests
test-module:
	@if [ -z "$(MODULE)" ]; then \
		echo "Usage: make test-module MODULE=<module_name>"; \
		exit 1; \
	fi
	python run_tests.py -m $(MODULE) -v

# Clean up temporary files
clean:
	rm -rf .coverage htmlcov .pytest_cache test-results.xml coverage.xml
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Help target
help:
	@echo "Available targets:"
	@echo "  all            : Run all tests (default)"
	@echo "  install        : Install the package"
	@echo "  install-dev    : Install in development mode"
	@echo "  install-test   : Install and run tests"
	@echo "  install-dev-test: Install in development mode and run tests"
	@echo "  test           : Run all tests"
	@echo "  test-coverage  : Run tests with coverage report"
	@echo "  test-html      : Run tests with HTML coverage report"
	@echo "  test-module    : Run tests for a specific module (e.g., make test-module MODULE=workflow)"
	@echo "  clean          : Clean up temporary files"
	@echo "  help           : Show this help message"
