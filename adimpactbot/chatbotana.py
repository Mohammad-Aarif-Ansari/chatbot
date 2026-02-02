"""
Chatbot module using OpenRouter API for LLM interactions.
Provides conversation management and AI-powered responses for sentiment analysis discussions.
"""

from typing import List, Dict, Any, Optional
import os
import logging
import json
import requests
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger("adimpact")

# Configuration - Hardcoded API key
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = "apikey"
# Use a model that's guaranteed to work on OpenRouter
# Options: gpt-3.5-turbo, gpt-4, meta-llama/llama-2-70b, mistral-7b, etc.
CHATBOT_MODEL = os.getenv("CHATBOT_MODEL", "gpt-3.5-turbo")
CHATBOT_MAX_TOKENS = int(os.getenv("CHATBOT_MAX_TOKENS", "1024"))
CHATBOT_TEMPERATURE = float(os.getenv("CHATBOT_TEMPERATURE", "0.7"))

# System prompt for the chatbot
SYSTEM_PROMPT = """You are AdImpact's intelligent assistant. You help users understand social media sentiment analysis, 
interpret comment data, and provide actionable insights based on analyzed comments. 
Be helpful, concise, and provide specific examples when relevant. 
Format responses in clear, readable paragraphs or bullet points."""


class ChatbotSession:
    """Manages a conversation session with the OpenRouter chatbot."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({
            "role": role,
            "content": content
        })
        self.last_accessed = datetime.now()
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get full conversation history."""
        return self.messages
    
    def is_expired(self, timeout_minutes=30) -> bool:
        """Check if session has expired."""
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        return elapsed > (timeout_minutes * 60)


# In-memory session storage (for production, use a database)
_chat_sessions: Dict[str, ChatbotSession] = {}


def create_chat_session(session_id: str) -> ChatbotSession:
    """Create a new chat session."""
    session = ChatbotSession(session_id)
    _chat_sessions[session_id] = session
    return session


def get_chat_session(session_id: str) -> Optional[ChatbotSession]:
    """Retrieve an existing chat session."""
    return _chat_sessions.get(session_id)


def chat_with_openrouter(user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a message to OpenRouter and get an AI response.
    
    Args:
        user_message: The user's input message
        session_id: Optional session ID for maintaining conversation context
        
    Returns:
        Dict with 'response' (str), 'session_id' (str), and 'status' (str)
        
    Raises:
        RuntimeError: If API key is not configured or API call fails
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key is not configured. Set OPENROUTER_API_KEY environment variable.")
    
    # Cleanup expired sessions (runs before each chat to avoid memory buildup)
    expired_ids = [
        sid for sid, sess in _chat_sessions.items() 
        if sess.is_expired()
    ]
    for expired_id in expired_ids:
        del _chat_sessions[expired_id]
        logger.info(f"🗑️  Cleaned up expired session: {expired_id[:20]}...")
    
    # Get or create session
    if session_id:
        session = get_chat_session(session_id)
        if not session:
            session = create_chat_session(session_id)
    else:
        import uuid
        session_id = str(uuid.uuid4())
        session = create_chat_session(session_id)
    
    # Add user message to history
    session.add_message("user", user_message)
    
    # Build messages for API call (include system prompt + conversation history)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(session.get_messages())
    
    try:
        # Call OpenRouter API
        logger.info(f"📤 Calling OpenRouter API: {OPENROUTER_BASE_URL}/chat/completions")
        logger.info(f"   Model: {CHATBOT_MODEL}")
        logger.info(f"   Messages count: {len(messages)}")
        
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://adimpact.local",
                "X-Title": "AdImpact"
            },
            json={
                "model": CHATBOT_MODEL,
                "messages": messages,
                "temperature": CHATBOT_TEMPERATURE,
                "max_tokens": CHATBOT_MAX_TOKENS,
            },
            timeout=30
        )
        
        logger.info(f"📥 OpenRouter Response Status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        
        # Extract response
        if "choices" not in data or len(data["choices"]) == 0:
            logger.error(f"Invalid OpenRouter response: no choices in {data}")
            raise ValueError("Invalid API response: no choices returned")
        
        ai_response = data["choices"][0]["message"]["content"]
        
        # Validate response is not empty
        if not ai_response or not ai_response.strip():
            logger.warning("OpenRouter returned empty response")
            raise ValueError("OpenRouter returned an empty response")
        
        # Add AI response to history
        session.add_message("assistant", ai_response)
        
        logger.info(f"✅ Chat session {session_id}: AI response generated successfully")
        
        return {
            "status": "success",
            "response": ai_response,
            "session_id": session_id
        }
        
    except requests.exceptions.Timeout:
        logger.exception("⏱️  OpenRouter request timed out after 30 seconds")
        raise RuntimeError("OpenRouter request timed out. Please try again.")
    except requests.exceptions.ConnectionError as e:
        logger.exception(f"🌐 Connection error to OpenRouter: {e}")
        raise RuntimeError(f"Connection error: unable to reach OpenRouter")
    except requests.exceptions.RequestException as e:
        logger.exception(f"❌ OpenRouter API request failed: {e}")
        raise RuntimeError(f"Failed to get response from OpenRouter: {str(e)}")
    except (KeyError, ValueError) as e:
        logger.exception(f"❌ Failed to parse OpenRouter response: {e}")
        raise RuntimeError(f"Invalid response from OpenRouter: {str(e)}")


def get_session_history(session_id: str) -> Optional[List[Dict[str, str]]]:
    """Retrieve conversation history for a session."""
    session = get_chat_session(session_id)
    if session:
        return session.get_messages()
    return None


def clear_session(session_id: str) -> bool:
    """Clear a chat session."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
        return True
    return False


def analyze_sentiment_with_context(
    comments: List[str], 
    user_query: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use the chatbot to provide contextual insights about sentiment analysis.
    
    Args:
        comments: List of comments to analyze
        user_query: Optional question from the user about the comments
        session_id: Optional session ID
        
    Returns:
        Dict with AI insights and context
    """
    if not comments:
        return {"status": "error", "message": "No comments provided"}
    
    # Build context message
    sample_comments = comments[:5]  # First 5 comments as context
    sample_text = "\n".join(f"- {c}" for c in sample_comments)
    
    context_message = f"""I have {len(comments)} comments to analyze. Here are some samples:

{sample_text}

{f"User question: {user_query}" if user_query else "Please provide insights about these comments."}"""
    
    try:
        result = chat_with_openrouter(context_message, session_id)
        result["comment_count"] = len(comments)
        return result
    except RuntimeError as e:
        logger.error(f"Error in sentiment analysis with context: {e}")
        return {
            "status": "error",
            "message": str(e),
            "comment_count": len(comments)
        }
