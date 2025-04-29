# Document Summarization API

A FastAPI-based service for summarizing documents using LLM. This API allows you to extract key information from various document formats (PDF, Word, text) and generate comprehensive summaries.

## Features

- Document text extraction from PDF, Word, and text files
- Image text extraction from PDFs using OCR (when available)
- Intelligent document chunking for processing large documents
- Content analysis to identify key points, facts, and terminology
- Coherent summary generation in Markdown format
- Batch processing of multiple documents in a folder
- Asynchronous task processing with status tracking
- MongoDB integration for task and result storage


## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. start nougat:
  ```
  nougat_api
  ```
5. Start the API server:
   ```
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Submit Document for Summarization

```
POST /api/tasks/document
```

Request body:
```json
{
  "file_path": "/path/to/document.pdf"
}
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Submit Folder for Batch Summarization

```
POST /api/tasks/folder
```

Request body:
```json
{
  "folder_path": "/path/to/documents/folder"
}
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Check Task Status

```
GET /api/tasks/{task_id}/status
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "updated_at": "2023-06-01T12:00:00Z"
}
```

### Get Task Result

```
GET /api/tasks/{task_id}/result
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "done",
  "file_path": "/path/to/document.pdf",
  "summary": "# Document Summary\n\n## Key Points\n...\n",
  "error": null,
  "created_at": "2023-06-01T11:00:00Z",
  "updated_at": "2023-06-01T12:00:00Z"
}
```
## Running the Application
Once installed and configured, run the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API usage

Go to ***http://localhost:8000/docs*** to view api documentation