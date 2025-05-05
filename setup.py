from setuptools import setup, find_packages

setup(
    name="code_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "codegen>=0.55.4",
        "PyGithub>=2.6.1",
        "pyngrok>=7.2.5",
        "requests>=2.32.3",
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

