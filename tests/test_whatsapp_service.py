import pytest
from unittest.mock import patch, MagicMock
import whatsapp_service as wa
import json

@pytest.fixture
def sample_whatsapp_payload():
    """Fixture for a sample WhatsApp text message payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "16505551111",
                        "phone_number_id": "PHONE_NUMBER_ID"
                    },
                    "contacts": [{"profile": {"name": "John Doe"}, "wa_id": "11234567890"}],
                    "messages": [{
                        "from": "11234567890",
                        "id": "MSG_ID",
                        "timestamp": "1603059201",
                        "text": {"body": "Hello, world!"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

def test_parse_whatsapp_message_success(sample_whatsapp_payload):
    """Test parsing a valid incoming WhatsApp message."""
    sender_phone, message_text = wa.parse_whatsapp_message(sample_whatsapp_payload)
    
    assert sender_phone == "11234567890"
    assert message_text == "Hello, world!"

def test_parse_whatsapp_message_invalid():
    """Test parsing an invalid or non-message payload."""
    invalid_payload = {"object": "something_else"}
    sender_phone, message_text = wa.parse_whatsapp_message(invalid_payload)
    
    assert sender_phone is None
    assert message_text is None

@patch('whatsapp_service.requests.post')
def test_send_whatsapp_message(mock_post):
    """Test the sending of a WhatsApp message."""
    # Mock a successful API response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    recipient_phone = "11234567890"
    message_text = "This is a reply."
    
    wa.send_whatsapp_message(recipient_phone, message_text)
    
    mock_post.assert_called_once()
    # Check the arguments passed to requests.post
    args, kwargs = mock_post.call_args
    assert f"/{wa.PHONE_NUMBER_ID}/messages" in args[0]
    headers = kwargs['headers']
    assert headers['Authorization'] == f"Bearer {wa.WHATSAPP_API_TOKEN}"
    payload = json.loads(kwargs['data'])
    assert payload['to'] == recipient_phone
    assert payload['text']['body'] == message_text 