from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .generator import generate_scraper_code

app = FastAPI(
    title="Crawl4AI RAG",
    description="Code generation API using Crawl4AI documentation",
    version="0.1.0"
)

class ScraperRequest(BaseModel):
    query: str  # User request (e.g., "Extract article titles and links from TechCrunch")

class ScraperResponse(BaseModel):
    generated_code: str

@app.post("/generate_scraper/", response_model=ScraperResponse)
async def generate_scraper(request: ScraperRequest):
    """Generate Crawl4AI scraper code based on user request."""
    try:
        code = generate_scraper_code(request.query)
        return {"generated_code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
