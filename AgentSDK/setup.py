from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trento_agent_sdk",
    packages=find_packages(),
    version="0.2.2",
    description="A Python SDK for AI agents built from scratch with a simple implementation of the Agent2Agent and ModelContext protocols",
    author="Arcangeli and Morandin",
    python_requires=">=3.8",
    install_requires=["pydantic", "google-genai", "aiohttp", "fastapi", "uvicorn"],
)
