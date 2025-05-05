from setuptools import setup, find_packages

setup(
    name="code_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyGithub>=1.55",
        "pyngrok>=5.1.0",
        "requests>=2.25.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=20.8b1",
            "flake8>=3.8.0",
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "code-agent=code_agent.runner:main",
        ],
    },
    python_requires=">=3.7",
    description="AI-powered code agent for GitHub repositories",
    author="Zeeeepa",
    author_email="info@zeeeepa.com",
    url="https://github.com/Zeeeepa/Code_agent",
)
