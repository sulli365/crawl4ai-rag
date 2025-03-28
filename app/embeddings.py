from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
import os
from supabase import create_client
from dotenv import load_dotenv
import time
from typing import List, Optional
from openai import AsyncOpenAI

load_dotenv()

supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
embedding_model = OpenAIEmbeddings()

async def generate_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    Generate an embedding for the given text using OpenAI.
    
    Args:
        text: The text to generate an embedding for
        model: Optional model name to use
        
    Returns:
        The embedding vector
    """
    try:
        from config import settings
        
        # Initialize OpenAI client
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Use specified model or default from settings
        embedding_model_name = model or settings.embedding_model
        
        # Generate embedding
        response = await openai_client.embeddings.create(
            model=embedding_model_name,
            input=text
        )
        
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        # Return a zero vector as fallback
        return [0.0] * 1536

def create_table_if_not_exists():
    """Create the vector store table if it doesn't exist."""
    try:
        # Check if table exists
        result = supabase_client.table("crawl4ai_docs").select("id", count="exact").limit(1).execute()
        print(f"Table exists with {result.count} records")
    except Exception as e:
        print(f"Table doesn't exist or error: {e}")
        print("Creating table...")
        
        # Create table with the required schema for vector storage
        supabase_client.table("crawl4ai_docs").create({
            "id": "uuid primary key default gen_random_uuid()",
            "content": "text",
            "metadata": "jsonb",
            "embedding": "vector(1536)"  # OpenAI embeddings are 1536 dimensions
        }).execute()
        
        # Create vector index
        supabase_client.sql("""
            create index on crawl4ai_docs 
            using ivfflat (embedding vector_cosine_ops)
            with (lists = 100);
        """).execute()
        
        print("Table created successfully")
        # Wait a moment for the table to be ready
        time.sleep(2)

def store_documents():
    """Store example documents in Supabase with embeddings."""
    # Ensure table exists
    create_table_if_not_exists()
    
    docs = [
        Document(page_content="AsyncWebCrawler is used to define the URLs to scrape."),
        Document(page_content="arun() executes the crawling and returns extracted data."),
        Document(page_content="Use magic=True in arun() to enable automatic extraction."),
    ]
    
    try:
        SupabaseVectorStore.from_documents(
            documents=docs,
            embedding=embedding_model,
            client=supabase_client,
            table_name="crawl4ai_docs"
        )
        print("✅ Docs embedded & stored!")
    except Exception as e:
        print(f"❌ Error storing documents: {e}")

if __name__ == "__main__":
    store_documents()
