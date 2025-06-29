import pytest
from unittest.mock import patch, MagicMock
import rag_service as rag
import json

@pytest.fixture
def mock_pinecone_index():
    """Fixture to create a mock Pinecone index."""
    return MagicMock()

@patch('rag_service.boto3.client')
def test_get_bedrock_embedding(mock_boto3_client):
    """Test the Bedrock embedding generation."""
    # Setup mock Bedrock runtime client
    mock_bedrock = MagicMock()
    mock_boto3_client.return_value = mock_bedrock
    
    # Setup mock response from Bedrock
    expected_embedding = [0.1, 0.2, 0.3]
    response_payload = json.dumps({'embedding': expected_embedding})
    mock_bedrock.invoke_model.return_value = {
        'body': MagicMock(read=MagicMock(return_value=response_payload.encode('utf-8')))
    }
    
    # Call the function
    text = "what is the wifi password?"
    embedding = rag.get_bedrock_embedding(text)
    
    # Assertions
    assert embedding == expected_embedding
    mock_boto3_client.assert_called_once_with(
        'bedrock-runtime',
        aws_access_key_id=rag.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=rag.AWS_SECRET_ACCESS_KEY,
        region_name=rag.AWS_REGION
    )
    mock_bedrock.invoke_model.assert_called_once()


@patch('rag_service.get_bedrock_embedding')
def test_query_pinecone(mock_get_embedding, mock_pinecone_index):
    """Test the Pinecone query function."""
    query_text = "where is the nearest restaurant?"
    namespace = "test-namespace"
    mock_embedding = [0.4, 0.5, 0.6]
    
    # Mock the embedding generation
    mock_get_embedding.return_value = mock_embedding
    
    # Mock the Pinecone query result
    mock_pinecone_index.query.return_value = {
        'matches': [
            {'metadata': {'text': 'The best restaurant is The Pizza Place.'}},
            {'metadata': {'text': 'You can also try The Burger Joint.'}}
        ]
    }
    
    # Call the function
    contexts = rag.query_pinecone(mock_pinecone_index, query_text, namespace)
    
    # Assertions
    mock_get_embedding.assert_called_once_with(query_text)
    mock_pinecone_index.query.assert_called_once_with(
        namespace=namespace,
        vector=mock_embedding,
        top_k=3,
        include_metadata=True
    )
    assert len(contexts) == 2
    assert contexts[0] == 'The best restaurant is The Pizza Place.' 