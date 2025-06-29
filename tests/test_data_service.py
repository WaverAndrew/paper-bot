import pytest
from unittest.mock import MagicMock, patch
import data_service as db

@pytest.fixture
def mock_db_client():
    """Fixture to create a mock Supabase client."""
    client = MagicMock()
    return client

def test_get_user_namespace_found(mock_db_client):
    """Test retrieving a namespace when the user exists."""
    phone_number = "1234567890"
    expected_namespace = "test_namespace"
    
    # Configure the mock client to simulate a successful API response
    mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'pinecone_namespace': expected_namespace}
    ]
    
    namespace = db.get_user_namespace(mock_db_client, phone_number)
    
    assert namespace == expected_namespace
    # Verify that the correct table and filter were used
    mock_db_client.table.assert_called_with('users')
    mock_db_client.table().select.assert_called_with('pinecone_namespace')
    mock_db_client.table().select().eq.assert_called_with('phone_number', phone_number)

def test_get_user_namespace_not_found(mock_db_client):
    """Test retrieving a namespace when the user does not exist."""
    phone_number = "0987654321"
    
    # Configure the mock client to simulate an empty response
    mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    namespace = db.get_user_namespace(mock_db_client, phone_number)
    
    assert namespace is None

def test_get_conversation_history(mock_db_client):
    """Test retrieving conversation history."""
    phone_number = "1234567890"
    history_data = [
        {'sender': 'user', 'message': 'Hello'},
        {'sender': 'bot', 'message': 'Hi there!'}
    ]
    
    # Configure the mock to return history data
    mock_db_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = list(reversed(history_data))

    history = db.get_conversation_history(mock_db_client, phone_number)
    
    assert history == history_data
    mock_db_client.table.assert_called_with('conversation_history')

def test_add_message_to_history(mock_db_client):
    """Test adding a message to the history."""
    phone_number = "1234567890"
    sender = "user"
    message = "This is a test message"
    
    # The insert call doesn't need to return anything, just to be called correctly
    mock_insert = mock_db_client.table.return_value.insert.return_value
    
    db.add_message_to_history(mock_db_client, phone_number, sender, message)
    
    mock_db_client.table.assert_called_with('conversation_history')
    mock_db_client.table().insert.assert_called_with({
        'user_phone_number': phone_number,
        'sender': sender,
        'message': message
    })
    mock_insert.execute.assert_called_once() 