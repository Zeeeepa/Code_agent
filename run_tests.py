#!/usr/bin/env python3
"""
Test runner script for Code Agent.

This script provides a convenient way to run all tests for the Code Agent project.
It supports various options like running specific test modules, generating coverage
reports, and controlling verbosity.

Usage:
    python run_tests.py [options]

Options:
    --module/-m MODULE    Run tests only for the specified module
    --verbose/-v          Increase verbosity
    --coverage/-c         Generate coverage report
    --html-cov/-H         Generate HTML coverage report
    --xml-report/-x       Generate XML coverage report
    --junit-report/-j     Generate JUnit XML report
    --no-capture/-s       Don't capture stdout/stderr
    --pdb                 Drop into debugger on failures
    --help                Show this help message
"""

import sys
import os
import argparse
import subprocess


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Code Agent tests")
    parser.add_argument(
        "-m", "--module", 
        help="Run tests only for the specified module (e.g., workflow, integration)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Increase verbosity"
    )
    parser.add_argument(
        "-c", "--coverage", 
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "-H", "--html-cov", 
        action="store_true", 
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "-x", "--xml-report", 
        action="store_true", 
        help="Generate XML coverage report"
    )
    parser.add_argument(
        "-j", "--junit-report", 
        action="store_true", 
        help="Generate JUnit XML report"
    )
    parser.add_argument(
        "-s", "--no-capture", 
        action="store_true", 
        help="Don't capture stdout/stderr"
    )
    parser.add_argument(
        "--pdb", 
        action="store_true", 
        help="Drop into debugger on failures"
    )
    
    return parser.parse_args()


def run_tests(args):
    """Run tests with the specified options."""
    # Base command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add no-capture
    if args.no_capture:
        cmd.append("-s")
    
    # Add PDB
    if args.pdb:
        cmd.append("--pdb")
    
    # Add JUnit report
    if args.junit_report:
        cmd.append("--junitxml=test-results.xml")
    
    # Add coverage
    if args.coverage or args.html_cov or args.xml_report:
        cmd.append("--cov=code_agent")
        cmd.append("--cov-report=term")
        
        if args.html_cov:
            cmd.append("--cov-report=html")
        
        if args.xml_report:
            cmd.append("--cov-report=xml")
    
    # Add specific module if requested
    if args.module:
        cmd.append(f"tests/test_{args.module}.py")
    else:
        cmd.append("tests/")
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ["pytest", "pytest-cov"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages for testing:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall them with:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False
    
    return True


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
