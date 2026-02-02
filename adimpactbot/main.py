"""
FastAPI backend for AdImpact chatbot
Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import logging

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbotana import (
    chat_with_openrouter,
    get_session_history,
    clear_session,
    analyze_sentiment_with_context
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adimpact")

# Create FastAPI app
app = FastAPI(title="AdImpact Chatbot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory
try:
    if os.path.exists(os.path.join(SCRIPT_DIR, "static")):
        app.mount("/static", StaticFiles(directory=os.path.join(SCRIPT_DIR, "static")), name="static")
    else:
        logger.info("Static files directory not found")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    status: str
    response: str
    session_id: str

class HistoryRequest(BaseModel):
    session_id: str

class SentimentContextRequest(BaseModel):
    comments: List[str]
    query: Optional[str] = None
    session_id: Optional[str] = None

# Root endpoint - serve HTML
@app.get("/", response_class=HTMLResponse)
async def root():
    html_file = os.path.join(SCRIPT_DIR, "chatbot.html")
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()
    return """
    <html>
    <head><title>AdImpact Chatbot</title></head>
    <body>
        <h1>AdImpact Chatbot API</h1>
        <p>API Documentation: <a href="/docs">/docs</a></p>
        <p><a href="/chatbot">Open Chatbot</a></p>
    </body>
    </html>
    """

# Serve chatbot page
@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page():
    html_file = os.path.join(SCRIPT_DIR, "chatbot.html")
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()
    raise HTTPException(status_code=404, detail="chatbot.html not found")

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Chat endpoint
@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(request: Request, payload: ChatRequest):
    """Send a message to the chatbot"""
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Chat request from {client_ip}: {payload.message[:50]}...")
    
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(payload.message) > 5000:
        raise HTTPException(status_code=400, detail="Message too long (max 5000 characters)")
    
    try:
        result = chat_with_openrouter(
            payload.message.strip(),
            payload.session_id
        )
        
        return ChatResponse(
            status=result["status"],
            response=result["response"],
            session_id=result["session_id"]
        )
    except Exception as e:
        logger.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# History endpoint
@app.post("/api/chat/history")
async def get_history(payload: HistoryRequest):
    """Get conversation history"""
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    history = get_session_history(payload.session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": payload.session_id,
        "messages": history,
        "message_count": len(history)
    }

# Delete session endpoint
@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    success = clear_session(session_id)
    
    if success:
        return {"status": "success", "message": f"Session {session_id} cleared"}
    else:
        return {"status": "not_found", "message": f"Session {session_id} not found"}

# Sentiment analysis endpoint
@app.post("/api/chat/analyze-with-context")
async def analyze_with_context(payload: SentimentContextRequest):
    """Analyze sentiment with context"""
    if not payload.comments or len(payload.comments) == 0:
        raise HTTPException(status_code=400, detail="At least one comment is required")
    
    try:
        result = analyze_sentiment_with_context(
            payload.comments,
            payload.query,
            payload.session_id
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Analysis failed"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in sentiment analysis")
        raise HTTPException(status_code=500, detail="Internal server error")

# CORS preflight
@app.options("/api/chat/message")
async def options_message():
    return {"status": "ok"}

@app.options("/api/chat/history")
async def options_history():
    return {"status": "ok"}

@app.options("/api/chat/session/{session_id}")
async def options_delete_session(session_id: str):
    return {"status": "ok"}

@app.options("/api/chat/analyze-with-context")
async def options_analyze():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
