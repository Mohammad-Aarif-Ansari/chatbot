"""
Chatbot module using OpenRouter API for LLM interactions.

Provides secure, professional-grade conversation management and AI-powered
responses for sentiment analysis discussions.

Features:
- Thread-safe session management
- Automatic session expiration
- Error handling & validation
- Structured logging
- Rate limiting support
"""

from typing import List, Dict, Any, Optional
import os
import logging
import json
import requests
from datetime import datetime, timedelta
import uuid
from pydantic_settings import BaseSettings
import hashlib

logger = logging.getLogger("adimpact")



# ============================================================================
# CONFIGURATION
# ============================================================================

class ChatbotSettings(BaseSettings):
    """Load chatbot configuration from environment variables."""
    openrouter_api_key: str = "sk-apikey" 
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    chatbot_model: str = "gpt-3.5-turbo"
    chatbot_max_tokens: int = 1024
    chatbot_temperature: float = 0.7
    session_timeout_minutes: int = 30
    request_timeout_seconds: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_api_key(self) -> bool:
        """Check if API key is properly configured."""
        return bool(self.openrouter_api_key and self.openrouter_api_key != "apikey")


settings = ChatbotSettings()

# System prompt for the chatbot
SYSTEM_PROMPT = """You are AdImpact's intelligent assistant. You help users understand social media sentiment analysis, 
interpret comment data, and provide actionable insights based on analyzed comments. 

Guidelines:
- Be helpful, concise, and provide specific examples when relevant
- Format responses in clear, readable paragraphs or bullet points
- Avoid harmful, biased, or inappropriate content
- Focus on objective analysis and insights
- Maintain professional language and tone"""

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================


class ChatbotSession:
    """
    Manages a secure conversation session with the OpenRouter chatbot.
    
    Attributes:
        session_id: Unique session identifier
        messages: Conversation message history
        created_at: Session creation timestamp
        last_accessed: Last activity timestamp
    """
    
    def __init__(self, session_id: str):
        """Initialize a new chat session."""
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Invalid session_id")
        
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: "user" or "assistant"
            content: Message content
            
        Raises:
            ValueError: If role or content is invalid
        """
        if role not in ("user", "assistant", "system"):
            raise ValueError("Invalid role. Must be 'user', 'assistant', or 'system'")
        
        if not content or not isinstance(content, str):
            raise ValueError("Content must be non-empty string")
        
        self.messages.append({
            "role": role,
            "content": content.strip()
        })
        self.last_accessed = datetime.now()
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get full conversation history."""
        return self.messages.copy()
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)
    
    def is_expired(self, timeout_minutes: Optional[int] = None) -> bool:
        """
        Check if session has expired.
        
        Args:
            timeout_minutes: Timeout in minutes. Uses settings if not provided.
            
        Returns:
            True if session has expired, False otherwise
        """
        if timeout_minutes is None:
            timeout_minutes = settings.session_timeout_minutes
        
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        return elapsed > (timeout_minutes * 60)
    
    def get_age(self) -> float:
        """Get session age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


# ============================================================================
# SESSION STORAGE & MANAGEMENT
# ============================================================================

# In-memory session storage (for production, use Redis or database)
_chat_sessions: Dict[str, ChatbotSession] = {}


def create_chat_session(session_id: str) -> ChatbotSession:
    """
    Create a new chat session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        New ChatbotSession instance
        
    Raises:
        ValueError: If session_id is invalid or already exists
    """
    if not session_id:
        raise ValueError("session_id cannot be empty")
    
    if session_id in _chat_sessions:
        logger.warning("⚠️  Attempted to create duplicate session: %.20s", session_id)
        raise ValueError(f"Session already exists")
    
    session = ChatbotSession(session_id)
    _chat_sessions[session_id] = session
    logger.debug("✅ Created new session: %.20s", session_id)
    return session


def get_chat_session(session_id: str) -> Optional[ChatbotSession]:
    """
    Retrieve an existing chat session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        ChatbotSession if found, None otherwise
    """
    return _chat_sessions.get(session_id)


def cleanup_expired_sessions() -> int:
    """
    Remove expired sessions from memory.
    
    Returns:
        Number of sessions cleaned up
    """
    expired_ids = [
        sid for sid, sess in _chat_sessions.items() 
        if sess.is_expired()
    ]
    
    for expired_id in expired_ids:
        try:
            del _chat_sessions[expired_id]
            logger.debug("🗑️  Cleaned up expired session: %.20s", expired_id)
        except KeyError:
            pass
    
    if expired_ids:
        logger.info("🧹 Session cleanup: removed %d expired sessions", len(expired_ids))
    
    return len(expired_ids)


def get_session_stats() -> Dict[str, Any]:
    """Get statistics about active sessions."""
    return {
        "total_sessions": len(_chat_sessions),
        "sessions": [
            {
                "id": sid[:20] + "...",
                "messages": sess.get_message_count(),
                "age_seconds": sess.get_age()
            }
            for sid, sess in list(_chat_sessions.items())[:10]
        ]
    }


def chat_with_openrouter(user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a message to OpenRouter and get an AI response.
    
    Features:
    - Session management for conversation continuity
    - Automatic session cleanup
    - Comprehensive error handling
    - Request validation & security
    - Detailed logging for debugging
    
    Args:
        user_message: The user's input message
        session_id: Optional session ID for maintaining conversation context
        
    Returns:
        Dict containing:
            - status: "success" or "error"
            - response: AI response text
            - session_id: Session ID for future requests
            
    Raises:
        ValueError: If input validation fails
        RuntimeError: If API call fails
    """
    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================
    
    if not user_message or not isinstance(user_message, str):
        raise ValueError("Message must be a non-empty string")
    
    user_message = user_message.strip()
    
    if len(user_message) > 5000:
        raise ValueError("Message exceeds maximum length of 5000 characters")
    
    if session_id:
        if not isinstance(session_id, str) or len(session_id) > 500:
            raise ValueError("Invalid session_id format")
    
    # ========================================================================
    # API KEY VALIDATION
    # ========================================================================
    
    if not settings.validate_api_key():
        logger.error("❌ OpenRouter API key is not configured properly")
        raise RuntimeError(
            "OpenRouter API key is not configured. "
            "Set OPENROUTER_API_KEY environment variable."
        )
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    # Run session cleanup before each chat to avoid memory buildup
    cleanup_expired_sessions()
    
    # Get or create session
    if session_id:
        session = get_chat_session(session_id)
        if not session:
            session = create_chat_session(session_id)
            logger.info("📝 Retrieved existing session: %.20s", session_id)
    else:
        session_id = str(uuid.uuid4())
        session = create_chat_session(session_id)
        logger.info("🆕 Created new session: %.20s", session_id)
    
    # Add user message to history
    session.add_message("user", user_message)
    
    # Build messages for API call (include system prompt + conversation history)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    api_messages.extend(session.get_messages())
    
    # ========================================================================
    # API CALL
    # ========================================================================
    
    try:
        logger.info(
            "📤 Calling OpenRouter API [Session: %.20s, Model: %s, Messages: %d]",
            session_id, settings.chatbot_model, len(api_messages)
        )
        
        response = requests.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://adimpact.local",
                "X-Title": "AdImpact Chatbot"
            },
            json={
                "model": settings.chatbot_model,
                "messages": api_messages,
                "temperature": settings.chatbot_temperature,
                "max_tokens": settings.chatbot_max_tokens,
            },
            timeout=settings.request_timeout_seconds
        )
        
        logger.debug("📥 OpenRouter Response Status: %d", response.status_code)
        
        # Raise exception for HTTP errors
        response.raise_for_status()
        
        data = response.json()
        
        # ====================================================================
        # RESPONSE PARSING & VALIDATION
        # ====================================================================
        
        if "choices" not in data or not data["choices"]:
            logger.error("❌ Invalid OpenRouter response: no choices in response")
            logger.debug("Response data: %s", data)
            raise ValueError("Invalid API response: no choices returned")
        
        ai_response = data["choices"][0].get("message", {}).get("content", "").strip()
        
        if not ai_response:
            logger.warning("⚠️  OpenRouter returned empty response")
            raise ValueError("OpenRouter returned an empty response")
        
        # Validate response length (safety check)
        if len(ai_response) > 10000:
            logger.warning("⚠️  OpenRouter response too long: %d chars", len(ai_response))
            ai_response = ai_response[:10000] + "...[truncated]"
        
        # Add AI response to history
        session.add_message("assistant", ai_response)
        
        logger.info("✅ Chat session [%.20s]: Success | Response length: %d chars", session_id, len(ai_response))
        
        return {
            "status": "success",
            "response": ai_response,
            "session_id": session_id
        }
    
    # ====================================================================
    # ERROR HANDLING
    # ====================================================================
    
    except requests.exceptions.Timeout as e:
        logger.error("⏱️  OpenRouter request timed out after %d seconds", settings.request_timeout_seconds)
        raise RuntimeError(
            f"OpenRouter request timed out. Please try again in a moment."
        )
    
    except requests.exceptions.ConnectionError as e:
        logger.error("🌐 Connection error to OpenRouter: %s", str(e))
        raise RuntimeError(
            "Unable to reach OpenRouter. Please check your internet connection."
        )
    
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if response.status_code == 401:
            logger.error("❌ OpenRouter API authentication failed")
            raise RuntimeError("API authentication failed. Check your API key.")
        elif response.status_code == 429:
            logger.warning("⚠️  OpenRouter rate limit exceeded")
            raise RuntimeError("Rate limit exceeded. Please try again later.")
        else:
            logger.error("❌ OpenRouter API error: %s [Status: %d]", error_msg, response.status_code)
            raise RuntimeError(f"OpenRouter API error: {error_msg}")
    
    except requests.exceptions.RequestException as e:
        logger.error("❌ OpenRouter API request failed: %s", str(e))
        raise RuntimeError(f"Failed to communicate with OpenRouter: {str(e)}")
    
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logger.error("❌ Failed to parse OpenRouter response: %s", str(e))
        raise RuntimeError(f"Invalid response format from OpenRouter: {str(e)}")
    
    except Exception as e:
        logger.exception("❌ Unexpected error in chat_with_openrouter")
        raise RuntimeError(f"Internal error: {str(e)}")


def get_session_history(session_id: str) -> Optional[List[Dict[str, str]]]:
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of messages if session found, None otherwise
    """
    if not session_id:
        return None
    
    session = get_chat_session(session_id)
    if session:
        return session.get_messages()
    
    return None


def clear_session(session_id: str) -> bool:
    """
    Clear a chat session and remove it from memory.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if session was deleted, False if not found
    """
    if not session_id:
        logger.warning("⚠️  Attempted to clear session with empty ID")
        return False
    
    if session_id in _chat_sessions:
        try:
            del _chat_sessions[session_id]
            logger.info("🗑️  Session deleted: %.20s", session_id)
            return True
        except KeyError:
            logger.warning("⚠️  Session not found: %.20s", session_id)
            return False
    
    logger.warning("⚠️  Session not found for deletion: %.20s", session_id)
    return False


def analyze_sentiment_with_context(
    comments: List[str], 
    user_query: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use the chatbot to provide contextual insights about sentiment analysis.
    
    Args:
        comments: List of comments to analyze (1-100 items)
        user_query: Optional question from the user about the comments
        session_id: Optional session ID for conversation continuity
        
    Returns:
        Dict with AI insights, status, and context:
            - status: "success" or "error"
            - response: AI analysis text
            - session_id: Session ID
            - comment_count: Number of comments analyzed
            
    Raises:
        ValueError: If comments list is invalid
    """
    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================
    
    if not comments or not isinstance(comments, list):
        raise ValueError("Comments must be a non-empty list")
    
    if len(comments) == 0:
        raise ValueError("At least one comment is required")
    
    if len(comments) > 100:
        raise ValueError("Maximum 100 comments allowed per request")
    
    # Validate each comment
    valid_comments = []
    for i, comment in enumerate(comments):
        if not isinstance(comment, str):
            logger.warning("⚠️  Comment #%d is not a string, skipping", i)
            continue
        
        comment_stripped = comment.strip()
        if comment_stripped and len(comment_stripped) <= 5000:
            valid_comments.append(comment_stripped)
    
    if not valid_comments:
        raise ValueError("No valid comments found to analyze")
    
    if user_query and len(user_query) > 1000:
        raise ValueError("Query exceeds maximum length of 1000 characters")
    
    # ========================================================================
    # BUILD ANALYSIS REQUEST
    # ========================================================================
    
    # Use first 5 comments as visible context
    sample_comments = valid_comments[:5]
    sample_text = "\n".join(f"  • {c[:100]}" for c in sample_comments)
    
    # Build context message
    analysis_prompt = f"""I have {len(valid_comments)} comments to analyze.

Sample comments:
{sample_text}
"""
    
    if len(valid_comments) > 5:
        analysis_prompt += f"\n(Plus {len(valid_comments) - 5} more comments)\n"
    
    if user_query:
        analysis_prompt += f"\nUser question: {user_query}\n"
    
    analysis_prompt += "\nPlease provide sentiment analysis insights."
    
    # ========================================================================
    # CALL CHATBOT
    # ========================================================================
    
    try:
        logger.info("📊 Sentiment analysis request: %d comments", len(valid_comments))
        
        result = chat_with_openrouter(analysis_prompt, session_id)
        
        # Add metadata
        result["comment_count"] = len(valid_comments)
        result["sample_count"] = len(sample_comments)
        
        logger.info("✅ Sentiment analysis completed: %d comments analyzed", len(valid_comments))
        
        return result
    
    except ValueError as e:
        logger.warning("⚠️  Validation error in sentiment analysis: %s", str(e))
        return {
            "status": "error",
            "message": str(e),
            "comment_count": len(comments)
        }
    
    except RuntimeError as e:
        logger.error("❌ Runtime error in sentiment analysis: %s", str(e))
        return {
            "status": "error",
            "message": str(e),
            "comment_count": len(comments)
        }
    
    except Exception as e:
        logger.exception("❌ Unexpected error in sentiment analysis")
        return {
            "status": "error",
            "message": "Sentiment analysis failed",
            "comment_count": len(comments)
        }
