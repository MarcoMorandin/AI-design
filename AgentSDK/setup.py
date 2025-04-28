from setuptools import find_packages, setup

setup(
    name="trento_agent_sdk",
    packages=find_packages(),
    version="0.1.0",
    description="A Python SDK for AI agents built from scratch",
    author="Arcangeli and Morandin",
    install_requires=["pydantic", "google-genai"],
)
