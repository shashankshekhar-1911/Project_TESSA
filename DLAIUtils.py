import os
import sys
from dotenv import load_dotenv, find_dotenv

class Utils:
  def __init__(self):
    pass
  
  def create_dlai_index_name(self, index_name):
    _ = load_dotenv(find_dotenv())
    groq_key = os.getenv("GROQ_API_KEY")
    return f'{index_name}-{groq_key[-36:].lower().replace("_", "-")}'
    
  def get_openai_api_key(self):
    _ = load_dotenv(find_dotenv())
    return os.getenv("OPENAI_API_KEY")
    
  def get_groq_api_key(self):
    _ = load_dotenv(find_dotenv())
    return os.getenv("GROQ_API_KEY")
  
  def get_pinecone_api_key(self):
    _ = load_dotenv(find_dotenv())
    return os.getenv("PINECONE_API_KEY")
