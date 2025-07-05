from config import model, index, groq_client
from .pdf_to_vector import process_and_index_pdfs


def query_rag(query):
    """
    Query the RAG system with a given question
    
    Args:
        query: The question to ask
    """
    # Debug: Check index statistics
    print("\nIndex Statistics:")
    stats = index.describe_index_stats()
    print(f"Total vectors in index: {stats.total_vector_count}")
    print(f"Index dimension: {stats.dimension}")
    print(f"Index metric: {stats.metric}")

    # Only process PDFs if there are no vectors in the index
    
    process_and_index_pdfs()
    
    # Get embedding and convert to list
    embed = model.encode(query).tolist()
    res = index.query(vector=embed, top_k=3, include_metadata=True)

    # Debug: Print query results
    print("\nQuery Results:")
    print(f"Number of matches found: {len(res['matches'])}")
    for i, match in enumerate(res['matches']):
        print(f"\nMatch {i+1}:")
        print(f"Score: {match['score']}")
        print(f"Source: {match['metadata'].get('source', 'N/A')}")
        print(f"Chunk {match['metadata'].get('chunk_index', 'N/A')} of {match['metadata'].get('total_chunks', 'N/A')}")

    contexts = [
        x['metadata']['text'] for x in res['matches']
    ]

    # Debug: Print contexts
    print("\nExtracted Contexts:")
    print(f"Number of contexts: {len(contexts)}")
    for i, context in enumerate(contexts):
        print(f"\nContext {i+1}:")
        print(f"Length: {len(context)} characters")
        print(f"Preview: {context[:200]}...")

    prompt_start = (
        "Answer the question based on the context below.\n\n"+
        "Context:\n"
    )

    prompt_end = (
        f"\n\nQuestion: {query}\nAnswer:"
    )

    prompt = (
        prompt_start + "\n\n---\n\n".join(contexts) + 
        prompt_end
    )

    print("\nFinal Prompt:")
    print(prompt)

    # Calculate max_tokens based on input length
    # Rough estimate: 1 token ≈ 4 characters
    input_tokens = len(prompt) // 4
    # Reserve 20% of context window for input
    max_input_tokens = 4096 * 0.2
    # Calculate available tokens for response
    max_response_tokens = int(4096 - max_input_tokens)
    # Use 80% of available tokens for response
    max_tokens = int(max_response_tokens * 0.8)
    
    print(f"\nToken Usage:")
    print(f"Estimated input tokens: {input_tokens}")
    print(f"Max response tokens: {max_tokens}")

    #Get the Summary using Llama 3.3 70B
    res = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that writes informative articles based on the given context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=max_tokens,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    print('-' * 80)
    print(res.choices[0].message.content)
    
    return res.choices[0].message.content


def intermediate_query_rag(query):
    """
    Query the RAG system with a given question
    
    Args:
        query: The question to ask
    """

    
    # Get embedding and convert to list
    embed = model.encode(query).tolist()
    res = index.query(vector=embed, top_k=3, include_metadata=True)

    # Debug: Print query results
    print("\nQuery Results:")
    print(f"Number of matches found: {len(res['matches'])}")
    for i, match in enumerate(res['matches']):
        print(f"\nMatch {i+1}:")
        print(f"Score: {match['score']}")
        print(f"Source: {match['metadata'].get('source', 'N/A')}")
        print(f"Chunk {match['metadata'].get('chunk_index', 'N/A')} of {match['metadata'].get('total_chunks', 'N/A')}")

    contexts = [
        x['metadata']['text'] for x in res['matches']
    ]

    return contexts[0]