from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trento_agent_sdk",
    packages=find_packages(),
    version="2.0.26",
    description="A Python SDK for AI agents built from scratch with a simple implementation of the Agent2Agent and ModelContext protocols",
    author="Arcangeli and Morandin",
    python_requires=">=3.8",
    install_requires=[
        "pydantic",
        "openai",
        "aiohttp",
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "anyio",
        "google-ai-generativelanguage",
        "google-generativeai",
        "google-api-core",
        "google-api-python-client",
        "google-auth",
        "flask",
        "httpx",
        "protobuf",
        "requests",
        "tqdm",
        "typing_extensions",
        "websockets",
        "google-genai",
    ],
)
