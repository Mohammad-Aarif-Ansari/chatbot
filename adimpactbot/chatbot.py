"""
Chatbot module for handling API requests and routing.
Provides conversation management and AI-powered responses.
"""

from typing import Optional, List, Dict, Any
import asyncio
import logging
import os
import time
import json

# Import chatbot functions from local module
from chatbotana import (
    chat_with_openrouter,
    get_session_history,
    clear_session,
    analyze_sentiment_with_context
)

logger = logging.getLogger("adimpact")

# Rate limiting configuration
CHAT_RATE_LIMIT_PER_MIN = int(os.getenv("CHAT_RATE_LIMIT_PER_MIN", "20"))
_chat_rate_store: dict = {}
_chat_rate_lock = asyncio.Lock()


def _is_chat_rate_limited(ip: str) -> bool:
    """Token bucket: CHAT_RATE_LIMIT_PER_MIN tokens per 60 seconds."""
    now = time.time()
    bucket = _chat_rate_store.get(ip)
    capacity = CHAT_RATE_LIMIT_PER_MIN
    refill_time = 60.0
    if not bucket:
        _chat_rate_store[ip] = {"tokens": capacity - 1, "last": now}
        return False
    tokens = bucket.get("tokens", 0)
    last = bucket.get("last", now)
    # refill
    refill = (now - last) * (capacity / refill_time)
    tokens = min(capacity, tokens + refill)
    if tokens < 1:
        bucket["tokens"] = tokens
        bucket["last"] = now
        return True
    bucket["tokens"] = tokens - 1
    bucket["last"] = now
    _chat_rate_store[ip] = bucket
    return False


class ChatRequest:
    """Request model for chat endpoint."""
    def __init__(self, message: str, session_id: Optional[str] = None):
        self.message = message
        self.session_id = session_id


class ChatResponse:
    """Response model for chat endpoint."""
    def __init__(self, status: str, response: str, session_id: str):
        self.status = status
        self.response = response
        self.session_id = session_id
    
    def to_dict(self):
        return {
            "status": self.status,
            "response": self.response,
            "session_id": self.session_id
        }


class HistoryRequest:
    """Request model for history endpoint."""
    def __init__(self, session_id: str):
        self.session_id = session_id


class SentimentContextRequest:
    """Request model for sentiment analysis with context."""
    def __init__(self, comments: List[str], query: Optional[str] = None, session_id: Optional[str] = None):
        self.comments = comments
        self.query = query
        self.session_id = session_id

def send_message(payload: ChatRequest, client_ip: str = "unknown") -> Dict[str, Any]:
    """
    Send a message to the chatbot and get an AI response.
    
    Args:
        payload: ChatRequest with message and optional session_id
        client_ip: Client IP for rate limiting
        
    Returns:
        Dict with status, response, and session_id
    """
    # Apply rate limiting
    if _is_chat_rate_limited(client_ip):
        logger.warning(f"🚫 Rate limit exceeded for {client_ip}")
        raise RuntimeError("Rate limit exceeded. Max 20 messages per minute.")
    
    logger.info(f"🔵 Incoming message from {client_ip}")
    logger.info(f"   Message: {payload.message[:50]}...")
    logger.info(f"   Session ID: {payload.session_id}")
    
    if not payload.message or not payload.message.strip():
        logger.warning("Message is empty")
        raise ValueError("Message cannot be empty")
    
    # Validate message length to prevent abuse
    MAX_MESSAGE_LENGTH = 5000
    if len(payload.message) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long: {len(payload.message)} chars")
        raise ValueError(f"Message too long (max {MAX_MESSAGE_LENGTH} characters)")
    
    # Validate session ID length
    if payload.session_id and len(payload.session_id) > 500:
        logger.warning(f"Session ID too long: {len(payload.session_id)} chars")
        raise ValueError("session_id is too long (max 500 characters)")
    
    try:
        logger.info("Calling chat_with_openrouter...")
        result = chat_with_openrouter(
            payload.message.strip(),
            payload.session_id
        )
        
        logger.info(f"✅ Success! Response status: {result['status']}")
        return result
    
    except RuntimeError as e:
        logger.exception("❌ Chatbot RuntimeError")
        raise RuntimeError(f"Chatbot error: {str(e)}")
    except Exception as e:
        logger.exception("❌ Unexpected error in chat endpoint")
        raise RuntimeError(f"Internal server error: {str(e)}")


def get_history(payload: HistoryRequest) -> Dict[str, Any]:
    """
    Get conversation history for a session.
    
    Args:
        payload: HistoryRequest with session_id
        
    Returns:
        Dict with session_id, messages, and message_count
    """
    if not payload.session_id:
        raise ValueError("session_id is required")
    
    history = get_session_history(payload.session_id)
    if history is None:
        raise ValueError("Session not found")
    
    return {
        "session_id": payload.session_id,
        "messages": history,
        "message_count": len(history)
    }


def delete_session_handler(session_id: str) -> Dict[str, Any]:
    """
    Clear a chat session.
    
    Args:
        session_id: The session ID to clear
        
    Returns:
        Dict with status and message
    """
    if not session_id:
        raise ValueError("session_id is required")
    
    success = clear_session(session_id)
    
    if success:
        return {"status": "success", "message": f"Session {session_id} cleared"}
    else:
        return {"status": "not_found", "message": f"Session {session_id} not found"}


def analyze_with_context_handler(payload: SentimentContextRequest) -> Dict[str, Any]:
    """
    Get AI insights about sentiment analysis for provided comments.
    
    Args:
        payload: SentimentContextRequest with comments, optional query, and session_id
        
    Returns:
        Dict with analysis results
    """
    if not payload.comments or len(payload.comments) == 0:
        raise ValueError("At least one comment is required")
    
    try:
        result = analyze_sentiment_with_context(
            payload.comments,
            payload.query,
            payload.session_id
        )
        
        if result.get("status") == "error":
            raise RuntimeError(result.get("message", "Analysis failed"))
        
        return result
    
    except Exception as e:
        logger.exception("Error in analyze_with_context")
        raise RuntimeError(f"Internal server error: {str(e)}")
