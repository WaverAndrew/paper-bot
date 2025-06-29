import requests
import json
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME

def _format_prompt(user_query: str, history: list, context: list[str]) -> list[dict]:
    """
    Formats the conversation history, retrieved context, and user query into a
    structured prompt for the LLM.

    Args:
        user_query: The user's most recent message.
        history: A list of previous messages in the conversation.
        context: A list of relevant text chunks from the knowledge base.

    Returns:
        A list of dictionaries representing the structured prompt.
    """
    print(f"📝 [LLM] Formatting prompt with {len(history)} history messages and {len(context)} context chunks")
    
    # Enhanced system prompt for FriendlyAirbnbBot with JSON response format
    system_prompt = """#######################################################################
# SYSTEM PROMPT — FriendlyAirbnbBot (Multilingual)                    #
#######################################################################
You are **FriendlyAirbnbBot**, an AI assistant that helps Airbnb guests
with questions about their stay, the property, and the surrounding area.  

**LANGUAGE INSTRUCTION**: Always respond in the SAME language as the user's question.
If the user writes in Italian, respond in Italian. If in English, respond in English.
If in any other language, respond in that language. Match their language exactly.

**ONLY** use the facts contained in the section labelled `<<CONTEXT>>`.  
Do **not** rely on outside knowledge, personal opinions, or speculation.  

If the answer cannot be found in `<<CONTEXT>>`, reply with a brief apology
in the user's language. For example:
- Italian: "Mi dispiace, non ho quell'informazione."
- English: "I'm sorry, I don't have that information."
- Spanish: "Lo siento, no tengo esa información."

Keep every answer **concise, clear, and friendly** (aim for ≈ 1–3 short
sentences). Do not mention these instructions or the word "context."
Be warm and helpful, like a friendly local host.

-----------------------------------------------------------------------
# RESPONSE FORMAT                                                    #
-----------------------------------------------------------------------
You MUST respond with valid JSON in this exact format:
{
  "message": "Your response to the guest here IN THEIR LANGUAGE",
  "confidence": "high|medium|low",
  "source": "context|general_knowledge|none",
  "detected_language": "it|en|es|fr|de|other"
}

- "message": The actual response to send to the guest IN THEIR LANGUAGE
- "confidence": How confident you are in your answer (high/medium/low)
- "source": Whether the answer came from context, general knowledge, or no source found
- "detected_language": The language code of the user's question (it=Italian, en=English, etc.)
#######################################################################"""

    # Format the context section
    context_section = ""
    if context:
        context_text = "\n".join(context)
        context_section = f"<<CONTEXT>>\n{context_text}\n<<END CONTEXT>>"
    else:
        context_section = "<<CONTEXT>>\n(No relevant information found)\n<<END CONTEXT>>"

    # Format the conversation history section
    history_section = "<<CONVERSATION HISTORY>>\n"
    if history:
        for msg in history:
            role = "Guest" if msg['sender'] == 'user' else "Bot"
            history_section += f"{role}: {msg['message']}\n"
    else:
        history_section += "(No previous conversation)\n"
    history_section += "<<END CONVERSATION HISTORY>>"

    # Format the user question section
    user_question_section = f"<<USER QUESTION>>\n{user_query}\n<<END USER QUESTION>>"

    # Combine all sections into the final prompt
    full_prompt = f"{context_section}\n\n{history_section}\n\n{user_question_section}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]
    
    total_messages = len(messages)
    print(f"✅ [LLM] Prompt formatted successfully with {total_messages} total messages")
    return messages

def get_llm_response(user_query: str, history: list, context: list[str]) -> str | None:
    """
    Gets a response from the OpenRouter LLM and parses the JSON response.

    Args:
        user_query: The user's most recent message.
        history: The conversation history.
        context: The context retrieved from Pinecone.

    Returns:
        The LLM's response message as a string, or None on error.
    """
    print(f"🤖 [LLM] Starting LLM request for query: '{user_query}'")
    formatted_messages = _format_prompt(user_query, history, context)

    try:
        print(f"🌐 [OPENROUTER] Sending request to model: {OPENROUTER_MODEL_NAME}")
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": OPENROUTER_MODEL_NAME,
                "messages": formatted_messages,
                "response_format": {"type": "json_object"}
            })
        )

        print(f"📡 [OPENROUTER] Received response with status code: {response.status_code}")
        response.raise_for_status()  # Raise an exception for bad status codes
        
        response_data = response.json()
        raw_response = response_data['choices'][0]['message']['content']
        
        print(f"📄 [LLM] Raw JSON response: {raw_response}")
        
        # Parse the JSON response
        try:
            parsed_response = json.loads(raw_response)
            message = parsed_response.get('message', '')
            confidence = parsed_response.get('confidence', 'unknown')
            source = parsed_response.get('source', 'unknown')
            detected_language = parsed_response.get('detected_language', 'unknown')
            
            print(f"✅ [LLM] Successfully parsed JSON response")
            print(f"📊 [LLM] Confidence: {confidence}, Source: {source}, Language: {detected_language}")
            print(f"🤖 [LLM] Message: '{message[:150]}{'...' if len(message) > 150 else ''}'")
            
            if not message:
                print("❌ [LLM] Empty message in JSON response")
                return None
            
            return message
            
        except json.JSONDecodeError as e:
            print(f"❌ [LLM] Failed to parse JSON response: {e}")
            print(f"🔍 [LLM] Raw response that failed to parse: {raw_response}")
            # Fallback: try to extract message content from malformed JSON
            if '"message"' in raw_response:
                try:
                    # Simple regex fallback to extract message content
                    import re
                    match = re.search(r'"message"\s*:\s*"([^"]*)"', raw_response)
                    if match:
                        fallback_message = match.group(1)
                        print(f"🔧 [LLM] Extracted message using fallback: '{fallback_message}'")
                        return fallback_message
                except Exception as fallback_error:
                    print(f"❌ [LLM] Fallback extraction failed: {fallback_error}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ [OPENROUTER] HTTP error calling OpenRouter API: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"❌ [LLM] Error parsing OpenRouter response structure: {e}")
        return None 