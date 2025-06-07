
## 📋 Documentation

- [Requirements Document](https://docs.google.com/document/d/1Rg7ZIygavuiE3DOsFQmwhyblYL-CnRjXOBtcYRM1h5M/edit?usp=sharing)
- [Architecture Document](https://excalidraw.com/#json=tlm4ij3seTYrBw5_hyGrL,mMxhkMBZm-MySTA1C1G4EQ)
- [Architecture Document (Backup)](./architecture.svg)
- [Evaluation Document](./Evaluation.pdf)
- [Final Presentation](./Final-Presentation.pdf)

## 🏗️ Project Structure

```
AI-design/
├── agents/                     # AI Agent Services
│   ├── orchestrator/          # Central coordinator agent
│   ├── agent-registry/        # Service discovery system
│   └── slave-agent/           # Specialized task agents
│       ├── drive-organizer/   # Google Drive organization
│       ├── exam-generator/    # Educational content generation
│       ├── question-answering/# RAG-based Q&A system
│       └── summarizer/        # Document summarization
├── webapp/                    # Web Application
│   ├── frontend/             # React.js frontend
│   ├── backend/              # FastAPI backend
│   └── drive-webhook/        # Google Drive integration
└── libraries/                # Reusable Libraries
    ├── power-ocr/           # PDF/Video OCR processing
    └── trento-agent-sdk/    # Agent communication SDK
```

## 📊 Agent Card Example
```json
{
  "name": "Drive Organizer Agent",
  "description": "An agent that organizes Google Drive folders for university courses into logical sections.",
  "url": "https://localhost:8080",
  "version": "1.0.0",
  "skills": [
    {
      "id": "organize-drive",
      "name": "Google Drive Folder Organization",
      "description": "Can organize Google Drive folders based on document content analysis",
      "tags": null,
      "examples": [
        "organize my course 'Introduction to Computer Science' for user 111369155660754322920",
        "reorganize my course materials for 'Data Structures' for user 111369155660754322920",
        "structure my university course 'Machine Learning Fundamentals' for user 111369155660754322920"
      ],
      "inputModes": null,
      "outputModes": null
    }
  ],
  "defaultInputModes": [
    "text/plain"
  ],
  "defaultOutputModes": [
    "text/plain"
  ],
  "provider": "University of Trento",
  "documentationUrl": "TODO"
}
```
