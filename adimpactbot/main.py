"""
FastAPI backend for AdImpact chatbot.

Secure, professional-grade chatbot API with:
- Environment-based configuration
- Secure CORS policy
- Input validation & rate limiting
- Structured logging
- Security headers

Run with: python -m uvicorn main:app --host 127.0.0.1 --port 8000
Or set environment variables: HOST, PORT, RELOAD, LOG_LEVEL
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import sys
import logging
import uuid
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbotana import (
    chat_with_openrouter,
    get_session_history,
    clear_session,
    analyze_sentiment_with_context
)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings(BaseSettings):
    """Load configuration from environment variables."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
    ]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # Security
    max_message_length: int = 5000
    max_session_id_length: int = 500
    request_timeout_seconds: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.strip("[]'\"").split(",")]
        return v


settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("adimpact")

# Create FastAPI app
app = FastAPI(
    title="AdImpact Chatbot API",
    version="2.0.0",
    description="Secure, AI-powered chatbot for social media sentiment analysis",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

# Add security middleware for trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)

# Add GZIP middleware for compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware with restricted settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["X-Request-ID"],
    max_age=3600,
)

# Add custom middleware for request tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.start_time = datetime.now()
    
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# Get the directory of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory if it exists
try:
    if os.path.exists(os.path.join(SCRIPT_DIR, "static")):
        app.mount("/static", StaticFiles(directory=os.path.join(SCRIPT_DIR, "static")), name="static")
    else:
        logger.info("ℹ️  Static files directory not found at: %s", os.path.join(SCRIPT_DIR, "static"))
except Exception as e:
    logger.warning("⚠️  Could not mount static files: %s", str(e))

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., min_length=1, max_length=5000, description="User message (1-5000 chars)")
    session_id: Optional[str] = Field(None, max_length=500, description="Optional session ID")
    
    @validator("message")
    def validate_message(cls, v):
        """Ensure message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or contain only whitespace")
        return v.strip()
    
    @validator("session_id")
    def validate_session_id(cls, v):
        """Validate session_id format."""
        if v and not (len(v) > 0 and len(v) <= 500):
            raise ValueError("Invalid session ID format")
        return v


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    status: str = Field(..., description="Response status: 'success' or 'error'")
    response: str = Field(..., description="AI response text")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class HistoryRequest(BaseModel):
    """Request model for conversation history."""
    session_id: str = Field(..., max_length=500, description="Session ID")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        """Validate session_id is not empty."""
        if not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()


class HistoryResponse(BaseModel):
    """Response model for conversation history."""
    session_id: str
    messages: List[dict]
    message_count: int
    created_at: Optional[str] = None


class SentimentContextRequest(BaseModel):
    """Request model for sentiment analysis with context."""
    comments: List[str] = Field(..., min_items=1, max_items=100, description="Comments to analyze (1-100)")
    query: Optional[str] = Field(None, max_length=1000, description="Optional analysis query")
    session_id: Optional[str] = Field(None, max_length=500, description="Optional session ID")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str

# ============================================================================
# ENDPOINTS
# ============================================================================

# Root endpoint - serve HTML
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root():
    """Serve the chatbot HTML interface."""
    html_file = os.path.join(SCRIPT_DIR, "chatbot.html")
    if os.path.exists(html_file):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            logger.error("❌ Error reading chatbot.html: %s", str(e))
            raise HTTPException(status_code=500, detail="Failed to load chatbot interface")
    
    return """
    <html>
    <head>
        <title>AdImpact Chatbot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>✨ AdImpact Chatbot API</h1>
        <p>Welcome! Here are your options:</p>
        <ul>
            <li><a href="/chatbot">Open Chatbot Interface</a></li>
            <li><a href="/api/docs">API Documentation</a></li>
            <li><a href="/health">Health Check</a></li>
        </ul>
    </body>
    </html>
    """


# Serve chatbot page
@app.get("/chatbot", response_class=HTMLResponse, tags=["UI"])
async def chatbot_page():
    """Serve the chatbot interactive page."""
    html_file = os.path.join(SCRIPT_DIR, "chatbot.html")
    if os.path.exists(html_file):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            logger.error("❌ Error reading chatbot.html: %s", str(e))
            raise HTTPException(status_code=500, detail="Failed to load chatbot interface")
    
    raise HTTPException(status_code=404, detail="Chatbot interface not found")


@app.get("/chatbot.js", tags=["UI"])
async def chatbot_js():
    """Serve the chatbot client JavaScript."""
    js_file = os.path.join(SCRIPT_DIR, "chatbot.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="chatbot.js not found")


@app.get("/chatbot.css", tags=["UI"])
async def chatbot_css():
    """Serve the chatbot CSS file."""
    css_file = os.path.join(SCRIPT_DIR, "chatbot.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="chatbot.css not found")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Check API health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


# Chat endpoint
@app.post("/api/chat/message", response_model=ChatResponse, tags=["Chat"], status_code=200)
async def send_message(request: Request, payload: ChatRequest):
    """
    Send a message to the chatbot and receive an AI-powered response.
    
    ## Parameters:
    - **message**: The user's message (1-5000 characters)
    - **session_id**: Optional session ID for conversation continuity
    
    ## Responses:
    - 200: Successful message processing
    - 400: Invalid request (empty message, too long, etc.)
    - 429: Rate limit exceeded
    - 500: Internal server error
    """
    client_ip = request.client.host if request.client else "unknown"
    request_id = request.state.request_id
    
    logger.info("🔵 Chat request [%s] from %s: %.50s...", request_id, client_ip, payload.message)
    
    try:
        result = chat_with_openrouter(
            payload.message,
            payload.session_id
        )
        
        logger.info("✅ Chat success [%s]: session=%s", request_id, result.get("session_id", "unknown"))
        
        # Add request ID to response
        result["request_id"] = request_id
        
        return ChatResponse(**result)
    
    except ValueError as e:
        logger.warning("⚠️  Validation error [%s]: %s", request_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    
    except RuntimeError as e:
        logger.error("❌ Runtime error [%s]: %s", request_id, str(e))
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    except Exception as e:
        logger.exception("❌ Unexpected error [%s]", request_id)
        if settings.debug:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Conversation history endpoint
@app.post("/api/chat/history", response_model=HistoryResponse, tags=["Chat"])
async def get_history(request: Request, payload: HistoryRequest):
    """
    Retrieve conversation history for a session.
    
    ## Parameters:
    - **session_id**: The session ID to retrieve history for
    
    ## Responses:
    - 200: History retrieved successfully
    - 400: Invalid session_id
    - 404: Session not found
    """
    request_id = request.state.request_id
    
    logger.info("📋 History request [%s] for session: %.20s...", request_id, payload.session_id)
    
    try:
        history = get_session_history(payload.session_id)
        
        if history is None:
            logger.warning("⚠️  History not found [%s] for session: %.20s", request_id, payload.session_id)
            raise HTTPException(
                status_code=404,
                detail=f"No conversation history found for session"
            )
        
        logger.info("✅ History retrieved [%s]: %d messages", request_id, len(history))
        
        return {
            "session_id": payload.session_id,
            "messages": history,
            "message_count": len(history),
            "created_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Error retrieving history [%s]", request_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# Delete session endpoint
@app.delete("/api/chat/session/{session_id}", tags=["Chat"])
async def delete_session(request: Request, session_id: str):
    """
    Delete a chat session and clear its history.
    
    ## Parameters:
    - **session_id**: The session ID to delete
    
    ## Responses:
    - 200: Session deleted successfully
    - 400: Invalid session_id
    - 404: Session not found
    """
    request_id = request.state.request_id
    
    if not session_id or len(session_id) > 500:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    logger.info("🗑️  Delete session [%s] for: %.20s", request_id, session_id)
    
    success = clear_session(session_id)
    
    if success:
        logger.info("✅ Session deleted [%s]", request_id)
        return {"status": "success", "message": "Session cleared", "request_id": request_id}
    else:
        logger.warning("⚠️  Session not found [%s]", request_id)
        raise HTTPException(status_code=404, detail="Session not found")


# Sentiment analysis endpoint
@app.post("/api/chat/analyze-with-context", tags=["Analysis"])
async def analyze_with_context(request: Request, payload: SentimentContextRequest):
    """
    Analyze sentiment with contextual insights from AI.
    
    ## Parameters:
    - **comments**: List of comments to analyze (1-100 items)
    - **query**: Optional analysis query
    - **session_id**: Optional session ID
    
    ## Responses:
    - 200: Analysis completed successfully
    - 400: Invalid request (missing comments, too many items, etc.)
    - 500: Analysis failed
    """
    request_id = request.state.request_id
    
    logger.info("📊 Sentiment analysis [%s]: %d comments", request_id, len(payload.comments))
    
    try:
        result = analyze_sentiment_with_context(
            payload.comments,
            payload.query,
            payload.session_id
        )
        
        if result.get("status") == "error":
            logger.error("❌ Analysis error [%s]: %s", request_id, result.get("message"))
            raise HTTPException(status_code=500, detail=result.get("message", "Analysis failed"))
        
        logger.info("✅ Analysis completed [%s]", request_id)
        result["request_id"] = request_id
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Unexpected error in sentiment analysis [%s]", request_id)
        raise HTTPException(status_code=500, detail="Sentiment analysis failed")


# ============================================================================
# CORS PREFLIGHT ENDPOINTS
# ============================================================================

@app.options("/api/chat/message", tags=["CORS"])
@app.options("/api/chat/history", tags=["CORS"])
@app.options("/api/chat/session/{session_id}", tags=["CORS"])
@app.options("/api/chat/analyze-with-context", tags=["CORS"])
async def options_handler():
    """Handle CORS preflight requests."""
    return {"status": "ok"}


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("⚠️  Validation error [%s]: %s", request_id, str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("❌ Unhandled exception [%s]", request_id)
    return HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize app on startup."""
    logger.info("🚀 AdImpact ChatBot API starting up...")
    logger.info("   Environment: %s", settings.environment)
    logger.info("   Debug: %s", settings.debug)
    logger.info("   CORS Origins: %s", settings.cors_origins)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 AdImpact ChatBot API shutting down...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🔧 Starting server with settings:")
    logger.info("   Host: %s", settings.host)
    logger.info("   Port: %s", settings.port)
    logger.info("   Reload: %s", settings.reload)
    logger.info("   Log Level: %s", settings.log_level)
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
