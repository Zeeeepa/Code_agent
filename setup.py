from setuptools import setup, find_packages

setup(
    name="code_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "codegen>=0.1.0",
        "PyGithub>=2.1.1",
        "pyngrok>=6.0.0",
        "requests>=2.31.0",
    ],
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

