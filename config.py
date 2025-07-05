import warnings
warnings.filterwarnings('ignore')
import os
import torch
from sentence_transformers import SentenceTransformer
from pinecone.pinecone import Pinecone
from pinecone import ServerlessSpec
import boto3
import groq
from dotenv import load_dotenv
import DLAIUtils
from DLAIUtils import Utils

# Disable tokenizers parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()

# Initialize utils
utils = Utils()

# AWS S3 setup
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_BUCKET = os.getenv('S3_BUCKET')
S3_PREFIX = os.getenv('S3_PREFIX', '')  # Optional prefix to filter PDFs
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Default to us-east-1 if not specified

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Set device
device = 'cuda' if torch.cuda.is_available() else 'cpu'
if device != 'cuda':
    print('Sorry no cuda.')

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2", device=device, trust_remote_code=True)

# Pinecone setup
PINECONE_API_KEY = utils.get_pinecone_api_key()
pinecone = Pinecone(api_key=PINECONE_API_KEY)
INDEX_NAME = utils.create_dlai_index_name('dl-ai')

# Global variables for index management
_index_initialized = False
_index = None

def get_index():
    """Get or initialize the Pinecone index."""
    global _index_initialized, _index
    
    if not _index_initialized:
        print(f"\n[DEBUG] Initializing index for the first time")
        try:
            # First check if index exists
            existing_indexes = [index.name for index in pinecone.list_indexes()]
            if INDEX_NAME not in existing_indexes:
                print(f"[DEBUG] Creating new index: {INDEX_NAME}")
                pinecone.create_index(
                    name=INDEX_NAME,
                    dimension=model.get_sentence_embedding_dimension(),
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            else:
                print(f"[DEBUG] Using existing index: {INDEX_NAME}")
            
            _index = pinecone.Index(INDEX_NAME)
            _index_initialized = True
            print(f"[DEBUG] Index initialization complete: {_index}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize index: {str(e)}")
            raise
    else:
        print(f"\n[DEBUG] Using already initialized index: {_index}")
    
    return _index

# Connect to the created index
index = get_index()
print(index)

# Connect to Groq
GROQ_API_KEY = utils.get_groq_api_key()
groq_client = groq.Groq(api_key=GROQ_API_KEY) 