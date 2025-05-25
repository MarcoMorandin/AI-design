# Exam Generator Agent

An A2A (Agent-to-Agent) server that creates academic exams based on content from Google Drive documents stored in MongoDB.

## Features

- **Document Retrieval**: Fetches document content from MongoDB using Google Drive file IDs
- **Exam Structure Generation**: Creates a well-structured exam outline with topics and question types
- **Question Generation**: Produces exam questions with answers based on document content
- **Multiple Formats**: Supports different exam types (quiz, test, final exam) and difficulty levels
- **Professional Formatting**: Outputs well-formatted exam documents in Markdown or plain text
- **Answer Keys**: Optionally includes detailed answer keys

## Quick Start

1. Copy the `.env.template` file to create your own `.env` file:
```bash
cp .env.template .env
```

2. Edit the `.env` file with your API keys and configuration:
```
GEMINI_API_KEY=your_api_key_here
MONGODB_URI=your_mongodb_connection_string
MONGODB_DB_NAME=drive_documents
MONGODB_COLLECTION=processed_files
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python exam_generator_a2a_server.py
```

5. Test the agent:
```bash
python test_exam_generator_client.py
```

## Docker Deployment

To deploy using Docker:

```bash
docker-compose up -d
```

## API Usage

The agent accepts requests via the A2A protocol. Example request:

```
Generate a quiz from document ID 12345abcde with 10 questions
```

Parameters you can specify:
- Document ID (required): The Google Drive file ID whose content is stored in MongoDB
- Exam type: quiz, test, final exam (default is quiz)
- Difficulty level: easy, moderate, difficult (default is moderate)
- Number of questions: any positive integer (default is 10)
- Format type: markdown, plain_text (default is markdown)
- Answer inclusion: whether to include answers (default is true)

## MongoDB Requirements

The agent expects your MongoDB collection to have documents with this structure:
- `google_document_id`: The ID of the Google Drive file
- `content`: The text content of the document
- `file_name`: The name of the file (optional)

## Integration with Other Agents

This agent can be used as part of a broader ecosystem, working with:
- **Drive Organizer Agent**: To organize course documents before generating exams
- **Summarizer Agent**: To summarize content for more concise exams
- **Orchestrator**: To handle user requests and route them to the appropriate agent
