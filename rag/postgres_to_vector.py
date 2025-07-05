import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from config import model, index, pinecone
from datetime import datetime

# Load environment variables
load_dotenv()

# Define the list of tables to process
TABLES_TO_PROCESS = [
    "tickets_ticket",
    "tickets_user",
    "tickets_comment",
    "tickets_organization",
    "tickets_inputneededchecklist",
    "tickets_inputneededglossary"
]

def connect_to_postgres():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {str(e)}")
        return None

def get_table_columns(conn, table_name):
    """
    Get all columns for a specific table
    
    Args:
        conn: PostgreSQL connection
        table_name: Name of the table
    Returns:
        list: List of column names
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
            """, (table_name,))
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting columns for table {table_name}: {str(e)}")
        return []

def get_data_from_postgres(conn, table_name, batch_size=100):
    """
    Fetch data from PostgreSQL in batches
    
    Args:
        conn: PostgreSQL connection
        table_name: Name of the table to read from
        batch_size: Number of records to fetch at once
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get total count
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records = cur.fetchone()['count']
            
            # Fetch data in batches
            offset = 0
            while offset < total_records:
                cur.execute(f"""
                    SELECT *
                    FROM {table_name}
                    ORDER BY id
                    LIMIT {batch_size}
                    OFFSET {offset}
                """)
                
                batch = cur.fetchall()
                if not batch:
                    break
                    
                yield batch
                offset += batch_size
                
    except Exception as e:
        print(f"Error fetching data from PostgreSQL: {str(e)}")

def convert_value_for_metadata(value):
    """
    Convert values to be compatible with Pinecone metadata
    
    Args:
        value: Value to convert
    Returns:
        Converted value that is compatible with Pinecone metadata
    """
    # Handle None/null values
    if value is None:
        return ""  # Convert None to empty string
        
    # Handle datetime objects
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def process_and_index_batch(batch, batch_number, table_name):
    """
    Process a batch of records and index them in Pinecone
    
    Args:
        batch: List of records from PostgreSQL
        batch_number: Current batch number for vector IDs
        table_name: Name of the source table
    """
    try:
        # Create text representation of each record
        texts = []
        metadatas = []
        
        for record in batch:
            # Combine all column values into a single text
            text_parts = []
            for col, value in record.items():
                if value is not None:  # Skip NULL values
                    text_parts.append(f"{col}: {value}")
            
            text = " | ".join(text_parts)
            texts.append(text)
            
            # Create metadata with all column values
            metadata = {
                'source': 'postgres',
                'table': table_name,
                'postgres_id': record.get('id', 'unknown'),
                'text': text
            }
            # Add all column values to metadata, converting datetime values
            for col, value in record.items():
                metadata[col] = convert_value_for_metadata(value)
            
            metadatas.append(metadata)
        
        # Generate embeddings
        print(f"Generating embeddings for batch of {len(texts)} records")
        embeddings = model.encode(texts)
        
        # Prepare vectors for Pinecone
        vectors = []
        for i, (text, meta) in enumerate(zip(texts, metadatas)):
            vector_id = f"pg_{table_name}_{batch_number}_{i}_{int(time.time())}"
            vectors.append({
                'id': vector_id,
                'values': embeddings[i].tolist(),
                'metadata': meta
            })
        
        # Upsert to Pinecone
        print(f"Upserting {len(vectors)} vectors to Pinecone")
        index.upsert(vectors=vectors)
        print("Successfully upserted vectors to Pinecone")
        
    except Exception as e:
        print(f"Error processing batch: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def process_tables(tables=None):
    """
    Process specified tables and index their data in Pinecone
    
    Args:
        tables: Optional list of tables to process. If None, uses TABLES_TO_PROCESS
    """
    if tables is None:
        tables = TABLES_TO_PROCESS
        
    # Connect to PostgreSQL
    conn = connect_to_postgres()
    if not conn:
        return
    
    try:
        # Process each table
        for table_name in tables:
            print(f"\nProcessing table: {table_name}")
            
            # Process data in batches
            batch_number = 0
            for batch in get_data_from_postgres(conn, table_name):
                print(f"\nProcessing batch {batch_number} from {table_name}")
                process_and_index_batch(batch, batch_number, table_name)
                batch_number += 1
        
        # Print final statistics
        stats = index.describe_index_stats()
        print("\nFinal Index Statistics:")
        print(f"Total vectors in index: {stats.total_vector_count}")
        print(f"Index dimension: {stats.dimension}")
        print(f"Index metric: {stats.metric}")
        
    finally:
        conn.close()