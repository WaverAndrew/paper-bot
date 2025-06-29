import boto3
import json
from pinecone import Pinecone
from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    EMBEDDING_MODEL
)

def init_pinecone():
    """Initializes and returns a Pinecone client."""
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX_NAME)

def get_bedrock_embedding(text: str) -> list[float]:
    """
    Generates an embedding for the given text using AWS Bedrock.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding, or an empty list on error.
    """
    try:
        print(f"🧠 [BEDROCK] Generating embedding for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        print(f"🔗 [BEDROCK] Connected to Bedrock in region: {AWS_REGION}")
        
        body = json.dumps({"inputText": text})
        print(f"📤 [BEDROCK] Sending request to model: {EMBEDDING_MODEL}")
        response = bedrock_client.invoke_model(
            body=body,
            modelId=EMBEDDING_MODEL,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response['body'].read())
        embedding = response_body['embedding']
        print(f"✅ [BEDROCK] Successfully generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        print(f"❌ [BEDROCK] Error generating bedrock embedding: {e}")
        return []

def query_pinecone(pinecone_index, query_text: str, namespace: str, top_k: int = 5) -> list[str]:
    """
    Queries the Pinecone index with a text query after generating its embedding.

    Args:
        pinecone_index: The initialized Pinecone index object.
        query_text: The user's original text query.
        namespace: The Pinecone namespace to search in.
        top_k: The number of top results to return.

    Returns:
        A list of strings containing the text from the top matching documents.
    """
    try:
        print(f"🔍 [RAG] Starting RAG query for: '{query_text}'")
        print(f"📂 [RAG] Using namespace: {namespace}")
        print(f"🎯 [RAG] Requesting top {top_k} results")
        
        # Get the embedding for the user's query
        query_embedding = get_bedrock_embedding(query_text)
        if not query_embedding:
            print("❌ [RAG] Failed to generate embedding, aborting Pinecone query")
            return []

        print(f"🔍 [PINECONE] Querying index with {len(query_embedding)}-dimensional vector")
        # Query Pinecone
        query_result = pinecone_index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        print(f"📊 [PINECONE] Query returned {len(query_result['matches'])} matches")
        
        # Extract text content from matches
        contexts = []
        for i, match in enumerate(query_result['matches']):
            try:
                score = match.get('score', 0)
                metadata = match.get('metadata', {})
                
                # Look for text content in the text field (now that it's been added)
                text_content = metadata.get('text', '')
                
                if text_content:
                    contexts.append(text_content)
                    text_preview = text_content[:100] if isinstance(text_content, str) else str(text_content)[:100]
                    print(f"📄 [PINECONE] Match {i+1}: Score={score:.3f}, Text='{text_preview}{'...' if len(str(text_content)) > 100 else ''}'")
                else:
                    print(f"⚠️  [PINECONE] Match {i+1}: No text content found in metadata")
                    
            except Exception as match_error:
                print(f"❌ [PINECONE] Error processing match {i+1}: {match_error}")
                continue
        
        if not contexts:
            print("❌ [RAG] No text content found in any Pinecone matches")
        else:
            print(f"✅ [RAG] Successfully retrieved {len(contexts)} context chunks")
        
        return contexts
        
    except Exception as e:
        print(f"❌ [RAG] Error querying Pinecone: {e}")
        import traceback
        print(f"🔍 [RAG] Full traceback: {traceback.format_exc()}")
        return [] 