import os
import time
from dotenv import load_dotenv
from rag.postgres_to_vector import process_tables
from rag.pdf_to_vector import process_and_index_pdfs
from rag.query_rag import query_rag

# Load environment variables
load_dotenv()

def run_pipeline():
    """
    Run the complete RAG pipeline:
    1. Process PDFs and upload to vector DB
    2. Process PostgreSQL tables and upload to vector DB
    3. Run RAG query example
    """
    print("Starting RAG pipeline...")
    
    # Step 1: Process PDFs
    print("\nStep 1: Processing PDFs...")
    process_and_index_pdfs()
    
    # Step 2: Process PostgreSQL tables
    print("\nStep 2: Processing PostgreSQL tables...")
    process_tables()

# Step 3: Sample RAG query
    print("\nStep 3: Printing sample RAG query...")
    query_rag("What is IVMS?")


if __name__ == "__main__":
    run_pipeline() 