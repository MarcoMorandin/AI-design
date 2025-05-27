#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="power-ocr",
    version="0.1.0",
    author="Arcangeli & Morandin",
    description="AI-powered transcription tools for PDF and video files",
    packages=find_packages(include=["power_ocr", "power_ocr.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pdf-transcribe=power_ocr.cli.pdf_cli:main",
            "video-transcribe=power_ocr.cli.video_cli:main",
        ],
    },
)
