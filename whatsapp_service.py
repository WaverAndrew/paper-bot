import requests
import json
from config import WHATSAPP_API_TOKEN, PHONE_NUMBER_ID

def parse_whatsapp_message(payload: dict) -> tuple[str, str] | tuple[None, None]:
    """
    Parses the incoming WhatsApp message payload.

    Args:
        payload: The raw JSON payload from the WhatsApp webhook.

    Returns:
        A tuple containing the sender's phone number and their message text.
        Returns (None, None) if the payload is not a valid message.
    """
    try:
        print("🔍 [WHATSAPP] Parsing incoming webhook payload")
        # Check if it's a valid WhatsApp message notification
        if (payload.get('entry') and
            payload['entry'][0].get('changes') and
            payload['entry'][0]['changes'][0].get('value') and
            payload['entry'][0]['changes'][0]['value'].get('messages')):
            
            message_details = payload['entry'][0]['changes'][0]['value']['messages'][0]
            print(f"📱 [WHATSAPP] Found message of type: {message_details.get('type', 'unknown')}")
            
            # We only want to process text messages
            if message_details['type'] == 'text':
                sender_phone = message_details['from']
                message_text = message_details['text']['body']
                print(f"✅ [WHATSAPP] Successfully parsed text message")
                print(f"📞 [WHATSAPP] Sender: {sender_phone}")
                print(f"💬 [WHATSAPP] Message: '{message_text}'")
                return sender_phone, message_text
            else:
                print(f"⚠️  [WHATSAPP] Skipping non-text message type: {message_details['type']}")
        else:
            print("⚠️  [WHATSAPP] Payload does not contain a valid message structure")
                
    except (KeyError, IndexError) as e:
        print(f"❌ [WHATSAPP] Error parsing WhatsApp payload: {e}")

    print("❌ [WHATSAPP] Failed to parse message, returning None")
    return None, None


def send_whatsapp_message(recipient_phone: str, message_text: str):
    """
    Sends a text message to a user via the WhatsApp Cloud API.

    Args:
        recipient_phone: The phone number of the recipient.
        message_text: The text to send.
    """
    print(f"📤 [WHATSAPP] Preparing to send message to: {recipient_phone}")
    print(f"💬 [WHATSAPP] Message content: '{message_text[:100]}{'...' if len(message_text) > 100 else ''}'")
    
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }

    try:
        print(f"🌐 [WHATSAPP] Sending POST request to WhatsApp API")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"📡 [WHATSAPP] Received response with status code: {response.status_code}")
        response.raise_for_status()
        print(f"✅ [WHATSAPP] Message sent successfully to {recipient_phone}")
    except requests.exceptions.RequestException as e:
        print(f"❌ [WHATSAPP] Error sending WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"❌ [WHATSAPP] Response content: {e.response.text}") 