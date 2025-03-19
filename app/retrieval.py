from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
embedding_model = OpenAIEmbeddings()

retriever = SupabaseVectorStore(
    client=supabase_client,
    embedding=embedding_model,
    table_name="crawl4ai_docs"
).as_retriever()

def retrieve_relevant_docs(query: str):
    """Fetches relevant Crawl4AI documentation snippets."""
    return retriever.get_relevant_documents(query)

if __name__ == "__main__":
    print(retrieve_relevant_docs("How to use arun()?"))
