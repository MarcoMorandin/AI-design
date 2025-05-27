# Markdown Summarizer A2. Edit the `.env` file with your API keys and configuration:
```
GEMINI_API_KEY=your_api_key_here
MONGODB_URI=your_mongodb_connection_string
MONGODB_DB_NAME=markdown_documents
MONGODB_COLLECTION=documents
```

3. Set up the development environment using the setup script:
```bash
./setup.sh
```

   Or manually install dependencies:
```bash
pip install -r requirements.txt
```elligent agent that takes markdown content from a database or direct text input, chunks it if necessary, summarizes each chunk in the requested style, and combines the summaries into a cohesive final document.

## Features

- **Retrieve documents by ID** from a database
- **Smart chunking** of large markdown documents to preserve semantic structure
- **Multiple summary styles**:
  - **Technical**: Preserves formulas, technical terms, and academic precision
  - **Bullet-points**: Creates hierarchical lists of key information
  - **Standard**: Produces flowing narrative summaries
  - **Concise**: Creates very brief summaries of essential information
  - **Detailed**: Comprehensive summaries with main points and supporting details
- **Maintains markdown formatting** in the summarized output

## Quick Start

1. Copy the `.env.template` file to create your own `.env` file:
```bash
cp .env.template .env
```

2. Edit the `.env` file with your API keys and configuration:
```
GEMINI_API_KEY=your_api_key_here
MONGODB_URI=your_mongodb_connection_string
MONGODB_DB_NAME=markdown_documents
MONGODB_COLLECTION=documents
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python markdown_summarizer_a2a_server.py
```

4. Test the agent:
```bash
# Test with direct markdown content
python test_markdown_summarizer_client.py

# Test with document ID
python test_markdown_summarizer_client.py --use-id --document-id doc123 --style bullet-points
```

## Docker Deployment

You can also use Docker to run the agent:

```bash
# Build and start the agent
docker-compose up -d

# View logs
docker-compose logs -f
```

## Available Styles

1. **Technical**: Preserves mathematical formulas, technical terms, and uses LaTeX formatting where appropriate.
2. **Bullet-points**: Creates hierarchical bullet-point lists that capture key information.
3. **Standard**: Creates a flowing narrative summary with cohesive paragraphs.
4. **Concise**: Creates a very brief summary focusing only on essential information.
5. **Detailed**: Creates a comprehensive summary with main points and supporting details.
