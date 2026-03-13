"""
Setup script for DevBot.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text()

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    content = requirements_file.read_text()
    # Parse requirements (skip [devbot] and version lines)
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('[') and not line.startswith('version'):
            requirements.append(line)

setup(
    name="devbot",
    version="1.0.0",
    description="AI Engineering Teammate - CLI plugin for AI-assisted development",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DevBot Team",
    author_email="devbot@example.com",
    url="https://github.com/devbot/devbot",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "devbot=devbot.cli.devbot_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Developer Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="ai developer tools claude openspec code-generation",
    project_urls={
        "Bug Reports": "https://github.com/devbot/devbot/issues",
        "Source": "https://github.com/devbot/devbot",
    },
)
