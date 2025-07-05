import warnings
warnings.filterwarnings('ignore')
import datasets
from datasets import load_dataset
from datasets.builder import DatasetGenerationError
import os
import time
import torch
from tqdm.auto import tqdm
import pandas as pd
import json
import requests
from pathlib import Path
import zipfile
import ast
from openai import OpenAI
import PyPDF2
import io
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from config import (
    model, index, groq_client,
    s3_client, S3_BUCKET, S3_PREFIX,
    device, utils, pinecone, INDEX_NAME
)

# Disable tokenizers parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()

# Your main.py specific code here...
