"""
AgentGraph - The Memory Layer for AI Agents
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="agentgraph",
    version="0.2.0",
    author="ICE-CUBA",
    description="The Memory Layer for AI Agents - Track, visualize, and share context between AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ICE-CUBA/AgentGraph",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "server": [
            "fastapi>=0.109.0",
            "uvicorn>=0.27.0",
            "pydantic>=2.5.0",
            "websockets>=12.0",
        ],
        "openai": [
            "openai>=1.12.0",
        ],
        "langchain": [
            "langchain>=0.1.0",
        ],
        "crewai": [
            "crewai>=0.28.0",
        ],
        "all": [
            "fastapi>=0.109.0",
            "uvicorn>=0.27.0",
            "pydantic>=2.5.0",
            "websockets>=12.0",
            "openai>=1.12.0",
            "langchain>=0.1.0",
            "crewai>=0.28.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agentgraph-server=agentgraph.api.server:run_server",
        ],
    },
    include_package_data=True,
    package_data={
        "agentgraph": ["dashboard/*.html"],
    },
)
