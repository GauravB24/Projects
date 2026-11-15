# Autonomous AI Agent

## Overview

This project is a Python-based Autonomous AI Agent built using FastAPI and Google Gemini (Free Tier). The agent accepts a natural language request, autonomously creates an execution plan, executes the planned tasks, and generates a professionally formatted Microsoft Word (.docx) document.

The project demonstrates autonomous planning, AI-powered content generation, document creation, REST API development, and engineering best practices such as retry and fallback mechanisms.

---

## Features

- Autonomous task planning using Google Gemini
- AI-driven document generation
- FastAPI REST API
- Microsoft Word (.docx) document generation
- Google Gemini Free Tier integration
- Retry mechanism with exponential backoff
- Fallback handling for malformed JSON responses
- Request validation using Pydantic
- Structured application logging
- Markdown to Word document formatting

---

## Technology Stack

- Python 3.12
- FastAPI
- Google Gemini 2.5 Flash
- python-docx
- Pydantic
- python-dotenv

---

## Project Structure

```
autonomous-ai-agent/
│
├── app/
│   ├── agent.py
│   ├── document_generator.py
│   ├── executor.py
│   ├── llm.py
│   ├── logger.py
│   ├── main.py
│   ├── models.py
│   ├── planner.py
│   └── prompts.py
│
├── output/
│
├── .env
├── requirements.txt
└── README.md
```

---

## API Endpoint

### POST `/agent`

### Request

```json
{
    "request": "Create a project proposal for an AI chatbot."
}
```

### Sample Response

```json
{
    "request": "Create a project proposal for an AI chatbot.",
    "plan": {
        "tasks": [
            {
                "title": "Executive Summary",
                "purpose": "Provide a high-level overview of the proposal."
            }
        ]
    },
    "document_path": "output/generated_document_xxxxx.docx",
    "status": "Completed"
}
```

---

## Engineering Improvement

This project implements **Retry & Fallback Logic** to improve reliability when interacting with the LLM.

### Retry

- Maximum of 3 retry attempts
- Exponential backoff (2s, 4s)
- Handles temporary API or network failures

### Fallback

If the planner receives malformed JSON from the LLM, it:

- Removes Markdown code fences
- Extracts the JSON object
- Attempts parsing again before failing

This minimizes unnecessary API calls and improves robustness when handling imperfect LLM responses.

---

## Running the Project

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root.

```
GEMINI_API_KEY=your_api_key_here
```

### Start the API

```bash
uvicorn app.main:app --reload
```

### Swagger Documentation

Open:

```
http://127.0.0.1:8000/docs
```

---

## Example Workflow

```
User Request
      │
      ▼
FastAPI Endpoint
      │
      ▼
Planner
      │
      ▼
Gemini LLM
      │
      ▼
Execution Plan
      │
      ▼
Executor
      │
      ▼
Gemini LLM
      │
      ▼
Generated Content
      │
      ▼
Document Generator
      │
      ▼
Microsoft Word (.docx)
```

---

## Future Improvements

- Conversation Memory
- Tool Calling
- Retrieval-Augmented Generation (RAG)
- Multi-Agent Architecture
- Database Integration
- Web Search Integration
- Export to PDF
- Async task execution