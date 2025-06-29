import pytest
from unittest.mock import patch, MagicMock
import llm_service as llm

def test_format_prompt():
    """Test the prompt formatting logic."""
    user_query = "Is breakfast included?"
    history = [
        {"sender": "user", "message": "Hi"},
        {"sender": "bot", "message": "Hello!"}
    ]
    context = ["Breakfast is served from 7 to 10 AM."]
    
    messages = llm._format_prompt(user_query, history, context)
    
    # Expected structure: system, system context, history, user query
    assert len(messages) == 5 
    assert messages[0]['role'] == 'system'
    assert "You are a friendly and helpful Airbnb assistant." in messages[0]['content']
    assert messages[1]['role'] == 'system'
    assert "CONTEXT" in messages[1]['content']
    assert messages[2]['role'] == 'user'
    assert messages[3]['role'] == 'bot'
    assert messages[4]['role'] == 'user'
    assert messages[4]['content'] == user_query

@patch('llm_service.requests.post')
def test_get_llm_response_success(mock_post):
    """Test a successful call to the OpenRouter API."""
    # Mock the response from the API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [{'message': {'content': 'Yes, breakfast is included.'}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    user_query = "Is breakfast included?"
    history = []
    context = []
    
    response = llm.get_llm_response(user_query, history, context)
    
    assert response == 'Yes, breakfast is included.'
    mock_post.assert_called_once()
    # You could add more detailed assertions here about the request payload

@patch('llm_service.requests.post')
def test_get_llm_response_api_error(mock_post):
    """Test handling of an API error from OpenRouter."""
    # Mock a failed request
    mock_post.side_effect = llm.requests.exceptions.RequestException("API is down")
    
    response = llm.get_llm_response("query", [], [])
    
    assert response is None 