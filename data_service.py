import supabase
from config import SUPABASE_URL, SUPABASE_KEY

def init_db_client():
    """Initializes and returns a Supabase client."""
    return supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_namespace(db_client, phone_number: str) -> str | None:
    """
    Retrieves the Pinecone namespace for a given user phone number.

    Args:
        db_client: The Supabase client instance.
        phone_number: The user's phone number.

    Returns:
        The Pinecone namespace as a string, or None if the user is not found.
    """
    try:
        print(f"🔍 [DATABASE] Querying users table for phone: {phone_number}")
        response = db_client.table('users').select('pinecone_namespace').eq('phone_number', phone_number).execute()
        if response.data:
            namespace = response.data[0]['pinecone_namespace']
            print(f"✅ [DATABASE] User found with namespace: {namespace}")
            return namespace
        print("❌ [DATABASE] No user found with this phone number")
        return None
    except Exception as e:
        print(f"❌ [DATABASE] Error fetching user namespace: {e}")
        return None

def get_conversation_history(db_client, phone_number: str, limit: int = 20) -> list:
    """
    Retrieves the last N messages from the conversation history for a user.
    The default is 20 messages.

    Args:
        db_client: The Supabase client instance.
        phone_number: The user's phone number.
        limit: The maximum number of messages to retrieve.

    Returns:
        A list of messages, where each message is a dictionary.
    """
    try:
        print(f"📚 [DATABASE] Fetching last {limit} messages for {phone_number}")
        response = db_client.table('conversation_history').select('sender, message').eq('user_phone_number', phone_number).order('timestamp', desc=True).limit(limit).execute()
        # The messages are fetched in reverse chronological order, so we reverse them back
        history = list(reversed(response.data))
        print(f"✅ [DATABASE] Found {len(history)} messages in conversation history")
        return history
    except Exception as e:
        print(f"❌ [DATABASE] Error fetching conversation history: {e}")
        return []

def add_message_to_history(db_client, phone_number: str, sender: str, message: str):
    """
    Adds a new message to the conversation history and trims the history to a
    maximum of 20 messages by deleting the oldest ones.

    Args:
        db_client: The Supabase client instance.
        phone_number: The user's phone number.
        sender: The sender of the message ('user' or 'bot').
        message: The content of the message.
    """
    try:
        print(f"💾 [DATABASE] Inserting {sender} message to history")
        # 1. Insert the new message
        db_client.table('conversation_history').insert({
            'user_phone_number': phone_number,
            'sender': sender,
            'message': message
        }).execute()
        print(f"✅ [DATABASE] Message inserted successfully")

        print(f"🧹 [DATABASE] Checking message count for cleanup...")
        # 2. Get all messages for the user to check the count
        all_messages_response = db_client.table('conversation_history').select('id, timestamp').eq('user_phone_number', phone_number).order('timestamp', desc=False).execute()
        
        all_messages = all_messages_response.data
        message_count = len(all_messages)
        print(f"📊 [DATABASE] Total messages for user: {message_count}")

        # 3. If count exceeds 20, delete the oldest ones
        if message_count > 20:
            num_to_delete = message_count - 20
            print(f"🗑️  [DATABASE] Deleting {num_to_delete} oldest messages to maintain 20-message limit")
            # Messages are already sorted oldest to newest, so we take the first few
            ids_to_delete = [msg['id'] for msg in all_messages[:num_to_delete]]
            
            if ids_to_delete:
                db_client.table('conversation_history').delete().in_('id', ids_to_delete).execute()
                print(f"✅ [DATABASE] Deleted {len(ids_to_delete)} old messages")
        else:
            print(f"✅ [DATABASE] No cleanup needed, message count within limit")

    except Exception as e:
        print(f"❌ [DATABASE] Error adding or trimming message history: {e}") 