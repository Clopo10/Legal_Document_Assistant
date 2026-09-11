# Legal Document Assistant

A RAG-based application for reviewing legal contracts. Upload a document, analyze compliance with Google Gemini, inspect flagged clauses, and ask questions about the contract.

## Stack

- Streamlit frontend
- FastAPI backend
- Qdrant vector database
- Hugging Face embeddings and Google Gemini

## Run with Docker

### 1. Set your API key

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
```

### 2. Start the application

```bash
docker compose up --build
```

Open the interface at [http://localhost:8501](http://localhost:8501).

The other services are available at:

- API: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Qdrant: [http://localhost:6333](http://localhost:6333)

Stop the services with:

```bash
docker compose down
```

It reads `.txt` files from `data/sample_contracts` and stores their embeddings in the local Qdrant collection.

## Project Layout

```text
backend/     FastAPI API and analysis engine
frontend/    Streamlit user interface
data/        Sample contracts and local Qdrant storage
scripts/     Data ingestion and evaluation utilities
```
