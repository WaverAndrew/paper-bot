from flask import Flask, request, jsonify
from config import WHATSAPP_VERIFY_TOKEN
import data_service as db
import rag_service as rag
import llm_service as llm
import whatsapp_service as wa

# Initialize Flask app
app = Flask(__name__)

# Initialize clients
db_client = db.init_db_client()
pinecone_index = rag.init_pinecone()

@app.route('/', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return "OK", 200

@app.route('/whatsapp', methods=['GET'])
def verify_webhook():
    """Handles webhook verification for the WhatsApp Cloud API."""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        print("Webhook verification failed.")
        return "Forbidden", 403

@app.route('/whatsapp', methods=['POST'])
def handle_message():
    """Handles incoming WhatsApp messages."""
    payload = request.get_json()
    
    print("🔄 [WEBHOOK] Received webhook payload")
    
    sender_phone, user_query = wa.parse_whatsapp_message(payload)
    
    if not sender_phone or not user_query:
        print("❌ [WEBHOOK] Invalid payload - not a processable message")
        return "OK", 200 # Not a message we can process, but acknowledge receipt

    print(f"✅ [WEBHOOK] Message parsed successfully")
    print(f"📱 [USER] From: {sender_phone}")
    print(f"💬 [USER] Message: '{user_query}'")

    # 1. Add user message to history
    print("🗃️  [DATABASE] Adding user message to conversation history...")
    db.add_message_to_history(db_client, sender_phone, 'user', user_query)
    print("✅ [DATABASE] User message added to history")

    # 2. Get user's Pinecone namespace
    print("🔍 [DATABASE] Looking up user's Pinecone namespace...")
    namespace = db.get_user_namespace(db_client, sender_phone)
    if not namespace:
        print("❌ [DATABASE] User not found in database")
        wa.send_whatsapp_message(sender_phone, "Sorry, I can't seem to find your user profile. Please contact support.")
        return "OK", 200
    print(f"✅ [DATABASE] Found namespace: {namespace}")
    
    # 3. Get conversation history
    print("📚 [DATABASE] Fetching conversation history...")
    history = db.get_conversation_history(db_client, sender_phone)
    print(f"✅ [DATABASE] Retrieved {len(history)} previous messages")

    # 4. Query Pinecone for context
    print("🔍 [RAG] Querying Pinecone for relevant context...")
    context = rag.query_pinecone(pinecone_index, user_query, namespace)
    print(f"✅ [RAG] Retrieved {len(context)} context chunks from Pinecone")
    
    # 5. Get response from LLM
    print("🤖 [LLM] Sending request to OpenRouter...")
    bot_response = llm.get_llm_response(user_query, history, context)
    
    if bot_response:
        print(f"✅ [LLM] Generated response: '{bot_response[:100]}{'...' if len(bot_response) > 100 else ''}'")
        # 6. Send response to user
        print("📤 [WHATSAPP] Sending response to user...")
        wa.send_whatsapp_message(sender_phone, bot_response)
        print("✅ [WHATSAPP] Message sent successfully")
        # 7. Add bot response to history
        print("🗃️  [DATABASE] Adding bot response to conversation history...")
        db.add_message_to_history(db_client, sender_phone, 'bot', bot_response)
        print("✅ [DATABASE] Bot response added to history")
        print("🎉 [COMPLETE] Pipeline completed successfully!")
    else:
        print("❌ [LLM] Failed to generate response")
        wa.send_whatsapp_message(sender_phone, "I'm sorry, I encountered an error and can't respond right now.")

    return "OK", 200

if __name__ == '__main__':
    # Use a production-ready WSGI server like Gunicorn or uWSGI instead of app.run() in production
    app.run(port=8080, debug=True) 