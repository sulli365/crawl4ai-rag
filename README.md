# Crawl4AI RAG

A Retrieval-Augmented Generation (RAG) system for generating Crawl4AI code snippets based on natural language queries.

## Features

- FastAPI server for code generation
- Supabase vector store for document storage and retrieval
- OpenAI GPT-4 for code generation
- LangChain for RAG implementation

## Setup

1. Install uv (if not already installed):
```bash
pip install uv
```

2. Create and activate virtual environment:
```bash
uv venv
# On Windows
.venv\Scripts\activate
# On Unix/MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
uv pip install .
```

4. Configure environment variables:
- Copy `.env.example` to `.env`
- Add your API keys:
  - OPENAI_API_KEY: Your OpenAI API key
  - SUPABASE_URL: Your Supabase project URL
  - SUPABASE_KEY: Your Supabase API key

## Usage

1. Store documentation embeddings:
```bash
python -m app.embeddings
```

2. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

3. Generate code via API:
```bash
curl -X POST "http://localhost:8000/generate_scraper/" \
     -H "Content-Type: application/json" \
     -d '{"query": "Extract article titles from TechCrunch"}'
```

Or visit http://localhost:8000/docs for the interactive API documentation.

## Project Structure

```
crawl4ai-rag/
│── .venv/       # Virtual environment (auto-managed by uv)
│── data/        # Store docs & embeddings (optional)
│── app/         # Application code
│   │── __init__.py
│   │── main.py          # FastAPI server
│   │── embeddings.py    # Handles embedding & Supabase storage
│   │── retrieval.py     # Handles retrieval from Supabase
│   │── generator.py     # Calls GPT-4 for code generation
│── pyproject.toml  # Dependency management
│── .env          # API keys
│── README.md     # This file
```

## Development

The application is built with modern Python tools and practices:
- uv for dependency management
- FastAPI for the web server
- Pydantic for data validation
- LangChain for RAG implementation
- Supabase for vector storage
- OpenAI GPT-4 for code generation

## License

MIT
