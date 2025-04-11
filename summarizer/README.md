# Summarizer Service

The Summarizer Service is a component of our AI system that processes transcribed text and generates concise summaries. It leverages advanced language models to extract key information from lengthy transcripts.

## Overview

This service receives transcribed text from the Transcriber Service, processes it through a summarization pipeline, and returns a condensed version that captures the essential content. The summarization process is designed to maintain the core meaning while significantly reducing the text length.

## Features

- Text summarization using state-of-the-art language models
- Configurable summarization parameters (length, focus areas)
- REST API for integration with other services
- Asynchronous processing for handling large documents
- Caching mechanism for improved performance

## Architecture

The Summarizer Service follows a modular architecture:

- **API Layer**: Handles HTTP requests and responses
- **Summarization Engine**: Core component that processes text and generates summaries
- **Model Manager**: Loads and manages the language models
- **Cache Manager**: Optimizes performance by storing recent results

## API Endpoints

### POST /summarize

Summarizes the provided text.

**Request Body:**
```json
{
  "text": "Long text to be summarized...",
  "max_length": 200,
  "min_length": 50
}


## Installation

1.  **Create and Activate a Virtual Environment:**
    ```bash
    python3.9 -m venv .venv
    source .venv/bin/activate
    # On Windows use: .venv\Scripts\activate
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
## Running the Application
Once installed and configured, run the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API usage

Go to ***http://localhost:8000/docs*** to view api documentation