import io
import PyPDF2
from tqdm.auto import tqdm
from config import (
    s3_client, S3_BUCKET, S3_PREFIX,
    model, index, groq_client
)

#List all PDF files in the S3 bucket
def list_pdfs_in_bucket():
    """List all PDF files in the S3 bucket"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PREFIX
        )
        
        pdf_keys = []
        for obj in response.get('Contents', []):
            if obj['Key'].lower().endswith('.pdf'):
                pdf_keys.append(obj['Key'])
                
        return pdf_keys
    except Exception as e:
        print(f"Error listing PDFs in bucket: {str(e)}")
        return []


def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes"""
    pdf_file = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def create_text_chunks(text, chunk_size=1000, overlap=200):
    """
    Split text into overlapping chunks
    
    Args:
        text (str): The text to split
        chunk_size (int): Size of each chunk
        overlap (int): Number of characters to overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        
    return chunks

def check_if_pdf_processed(pdf_key):
    """Check if a PDF has already been processed by querying the index"""
    try:
        # Create a test query using the PDF filename
        test_query = f"filename:{pdf_key.split('/')[-1]}"
        # Get embedding for the test query
        embed = model.encode(test_query).tolist()
        # Query the index
        res = index.query(vector=embed, top_k=1, include_metadata=True)
        # If we find any matches with this filename, the PDF has been processed
        return len(res['matches']) > 0
    except Exception as e:
        print(f"Error checking if PDF is processed: {str(e)}")
        return False

def process_and_index_pdfs(batch_size=1, chunk_size=1000, overlap=200):
    """
    Process PDFs from S3 and index them in Pinecone with text chunking
    
    Args:
        batch_size (int): Number of PDFs to process in each batch
        chunk_size (int): Size of each text chunk
        overlap (int): Number of characters to overlap between chunks
    """
    # Get list of PDFs
    pdf_keys = list_pdfs_in_bucket()
    print(f"Found {len(pdf_keys)} PDFs in bucket")
    
    # Filter out already processed PDFs
    unprocessed_pdfs = [pdf_key for pdf_key in pdf_keys if not check_if_pdf_processed(pdf_key)]
    print(f"Found {len(unprocessed_pdfs)} new PDFs to process")
    
    if not unprocessed_pdfs:
        print("No new PDFs to process")
        return
    
    # Process PDFs in batches
    for i in tqdm(range(0, len(unprocessed_pdfs), batch_size)):
        batch_keys = unprocessed_pdfs[i:i + batch_size]
        all_chunks = []
        all_metadata = []
        
        # Process each PDF in the batch
        for pdf_key in batch_keys:
            try:
                print(f"Processing PDF: {pdf_key}")
                response = s3_client.get_object(Bucket=S3_BUCKET, Key=pdf_key)
                pdf_bytes = response['Body'].read()
                text = extract_text_from_pdf(pdf_bytes)
                
                if text:
                    # Split text into overlapping chunks
                    chunks = create_text_chunks(text, chunk_size, overlap)
                    print(f"Created {len(chunks)} chunks for {pdf_key}")
                    
                    # Create metadata for each chunk
                    for chunk_idx, chunk in enumerate(chunks):
                        all_chunks.append(chunk)
                        all_metadata.append({
                            'source': f"s3://{S3_BUCKET}/{pdf_key}",
                            'filename': pdf_key.split('/')[-1],
                            'chunk_index': chunk_idx,
                            'total_chunks': len(chunks),
                            'text': chunk  # Store full chunk text in metadata
                        })
                else:
                    print(f"No text extracted from PDF: {pdf_key}")
            except Exception as e:
                print(f"Error processing PDF {pdf_key}: {str(e)}")
        
        if all_chunks:
            try:
                # Process chunks in smaller batches for embedding
                for j in range(0, len(all_chunks), 100):  # Process 100 chunks at a time for embedding
                    chunk_batch = all_chunks[j:j + 100]
                    meta_batch = all_metadata[j:j + 100]
                    
                    # Generate embeddings
                    print(f"Generating embeddings for batch of {len(chunk_batch)} chunks")
                    embeddings = model.encode(chunk_batch)
                    
                    # Prepare vectors for Pinecone
                    vectors = []
                    for k, (chunk, meta) in enumerate(zip(chunk_batch, meta_batch)):
                        vector_id = f"doc_{i}_{j}_{k}"
                        vectors.append({
                            'id': vector_id,
                            'values': embeddings[k].tolist(),
                            'metadata': meta
                        })
                    
                    # Upsert to Pinecone
                    print(f"Upserting {len(vectors)} vectors to Pinecone")
                    index.upsert(vectors=vectors)
                    print("Successfully upserted vectors to Pinecone")
            except Exception as e:
                print(f"Error in batch processing: {str(e)}")
        else:
            print("No texts to process in this batch")
            
    print("Finished processing and indexing PDFs")

# Remove the automatic execution at the bottom of the file
process_and_index_pdfs()

