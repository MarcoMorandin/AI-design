# Video to Essay API

This FastAPI application accepts a video URL, downloads the video, extracts the audio, transcribes it using OpenAI Whisper, generates a structured essay using an Ollama language model, and stores the results asynchronously in MongoDB. It provides endpoints to submit tasks, check their status, and retrieve the final essay.


## Prerequisites

Before you begin, ensure you have the following installed and running:

1.  **Python:** Version 3.9.
2.  **FFmpeg:** **Crucial external dependency.** MoviePy and Whisper rely heavily on FFmpeg being installed and accessible in your system's PATH.
    *   **macOS:** `brew install ffmpeg`
    *   **Ubuntu/Debian:** `sudo apt update && sudo apt install ffmpeg`
    *   **Windows:** Download from the official FFmpeg website and add it to your system's PATH.
3.  **Ollama:** A running instance of Ollama. The API needs to be accessible from where you run this application. Ensure you have pulled the desired model.

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