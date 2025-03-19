from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_openai import ChatOpenAI
from .retrieval import retriever
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

def generate_scraper_code(user_query: str) -> str:
    """Generates Crawl4AI code based on user request."""
    return qa_chain.run(user_query)

if __name__ == "__main__":
    print(generate_scraper_code("Extract article titles from TechCrunch"))
