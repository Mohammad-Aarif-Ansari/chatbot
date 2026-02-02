# AdImpact Chatbot - Setup & Running Guide

## Overview
AdImpact is an AI-powered chatbot for social media sentiment analysis and insights. It uses FastAPI for the backend and integrates with OpenRouter AI API.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Server
**Windows:**
```bash
run_server.bat
```

**Linux/Mac:**
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open in Browser
```
http://localhost:8000
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- fastapi==0.104.1
- uvicorn==0.24.0
- pydantic==2.5.0
- requests

### Verify Installation
```bash
python -c "import fastapi, uvicorn, requests; print('✓ All dependencies installed!')"
```

## Running the Server

### Option 1: Windows Batch Script
Simply double-click `run_server.bat` in the adimpactbot folder.

### Option 2: Manual Command Line
```bash
cd adimpactbot
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:adimpact:Static files directory not found
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Option 3: Shell Script (Linux/Mac)
```bash
chmod +x start.sh
./start.sh
```

## Accessing the Chatbot

### Browser Interface
Once the server is running:
- **Chatbot**: http://localhost:8000
- **Chatbot Page**: http://localhost:8000/chatbot
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Testing

### Core Functionality Tests
Tests the Python chatbot engine:
```bash
python test_core.py
```

Tests:
- ✓ Session creation
- ✓ Chat message processing
- ✓ Conversation history
- ✓ Sentiment analysis
- ✓ Session management

### Simple API Tests
Tests the HTTP endpoints:
```bash
python test_api_simple.py
```

Tests:
- ✓ Server connectivity
- ✓ Health endpoint
- ✓ Root endpoint
- ✓ Chat endpoint

### Complete Test Suite
```bash
python test_complete.py
```

## Configuration

### API Key
The OpenRouter API key is set in `chatbotana.py` line 18:
```python
OPENROUTER_API_KEY = "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"
```

To use a different key, edit this line.

### Server Settings
Edit `main.py` to modify:
- **Host**: Line with `--host` parameter (default: 0.0.0.0)
- **Port**: Change port 8000 to desired port (default: 8000)
- **CORS**: Lines 33-40 in main.py
- **Model**: Edit chatbotana.py for model selection

### Chatbot Settings
Edit `chatbotana.py` to modify:
- **Model**: `model="gpt-3.5-turbo"` (line ~110)
- **Session Expiry**: 30 minutes (line ~40)
- **Rate Limit**: 20 messages/minute per IP

## API Endpoints

### GET /
Returns the chatbot HTML interface

### GET /health
Health check
```json
{"status": "ok"}
```

### POST /api/chat/message
Send a message to the chatbot
```json
{
  "message": "Your message here",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "status": "success",
  "response": "AI response here",
  "session_id": "your-session-id"
}
```

### POST /api/chat/history
Get conversation history
```json
{
  "session_id": "your-session-id"
}
```

### DELETE /api/chat/session/{session_id}
Clear a conversation session

### POST /api/chat/analyze-with-context
Analyze sentiment of comments
```json
{
  "comments": ["comment 1", "comment 2"],
  "query": "analysis context",
  "session_id": "optional-session-id"
}
```

## File Structure

```
adimpactbot/
├── main.py                 # FastAPI backend server
├── chatbotana.py          # Core chatbot logic & OpenRouter API
├── chatbot.html           # Web interface
├── chatbot.css            # Styling
├── chatbot.js             # Frontend JavaScript
├── requirements.txt       # Python dependencies
├── run_server.bat         # Windows startup
├── start.sh              # Linux/Mac startup
├── test_core.py          # Core tests
├── test_api_simple.py    # API tests
├── test_complete.py      # Full integration tests
└── README.md             # This file
```

## Troubleshooting

### Port 8000 Already in Use
```bash
# Use a different port
python -m uvicorn main:app --port 8001
```

### "Module not found" Error
Make sure you're in the correct directory:
```bash
cd adimpactbot
python main.py  # or uvicorn command
```

### 405 Method Not Allowed
- Server not running? Check http://localhost:8000/health
- Clear browser cache (Ctrl+Shift+Delete)
- Check browser console: F12 > Console tab
- Verify URL is http://localhost:8000 (not file://)

### Empty API Responses
- Check API key is valid in chatbotana.py line 18
- Verify API account has sufficient credits
- Check internet connection

### "Connection Refused"
- Is the server running? (should see "Uvicorn running" message)
- Is it on the correct port? (default 8000)
- Check firewall settings

## Deploying to Production

For production deployment, replace:
```bash
python -m uvicorn main:app --reload
```

With:
```bash
python -m uvicorn main:app --workers 4
```

And use a production ASGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## Development

### Adding New Endpoints
Edit `main.py` and add:
```python
@app.post("/api/your/endpoint")
async def your_endpoint(payload: YourModel):
    return {"response": "your response"}
```

### Modifying Chatbot Logic
Edit `chatbotana.py` for:
- Message processing
- Sentiment analysis
- Session management

### UI Changes
Edit `chatbot.html`, `chatbot.css`, `chatbot.js`

## Support

- **OpenRouter Docs**: https://openrouter.ai/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OpenRouter Models**: https://openrouter.ai/models

## Notes

- Sessions stored in-memory (cleared on restart)
- Session expiry: 30 minutes of inactivity
- Rate limit: 20 messages/minute per IP
- CORS enabled for all origins

├── chatbot.html            # Frontend UI
├── chatbot.js              # Frontend JavaScript
├── chatbot.css             # Frontend styles
├── test_chatbot.py         # Test suite
└── README.md               # This file
```

## Architecture

The project is completely **standalone** (no Flask/FastAPI required):

- **chatbotana.py**: Core engine with:
  - `ChatbotSession` class for session management
  - OpenRouter API integration
  - Conversation history tracking
  - Sentiment analysis with context
  
- **chatbot.py**: Business logic layer with:
  - Request validation
  - Rate limiting (token bucket algorithm)
  - Error handling
  - Handler functions for different operations

## Quick Start

### 1. Set Your API Key

Edit [chatbotana.py](chatbotana.py) line 18:

```python
OPENROUTER_API_KEY = "sk-your-api-key-here"  # Replace with your actual key
```

### 2. Install Dependencies

```bash
pip install requests
```

### 3. Test the Installation

```bash
python test_chatbot.py
```

Expected output:
```
[TEST 1] Importing from chatbotana...
[OK] chatbotana imported successfully
...
[SUCCESS] All tests passed!
```

## Usage Examples

### Example 1: Send a Chat Message

```python
from chatbot import send_message, ChatRequest

# Create a request
request = ChatRequest(
    message="What is sentiment analysis?",
    session_id="user-session-123"
)

# Send message
try:
    response = send_message(request, client_ip="192.168.1.1")
    print(f"Status: {response['status']}")
    print(f"Response: {response['response']}")
    print(f"Session: {response['session_id']}")
except Exception as e:
    print(f"Error: {e}")
```

### Example 2: Get Conversation History

```python
from chatbot import get_history, HistoryRequest

history_req = HistoryRequest(session_id="user-session-123")
result = get_history(history_req)

print(f"Messages in session: {result['message_count']}")
for msg in result['messages']:
    print(f"[{msg['role']}] {msg['content']}")
```

### Example 3: Analyze Sentiment with Context

```python
from chatbot import analyze_with_context_handler, SentimentContextRequest

comments = [
    "This product is amazing!",
    "I don't like the quality",
    "Good value for money"
]

request = SentimentContextRequest(
    comments=comments,
    query="What do customers think about product quality?"
)

result = analyze_with_context_handler(request)
print(result['response'])
```

### Example 4: Clear a Session

```python
from chatbot import delete_session_handler

result = delete_session_handler("user-session-123")
print(result['message'])  # "Session user-session-123 cleared"
```

## Configuration

### Environment Variables (Optional)

```bash
export CHATBOT_MODEL="gpt-3.5-turbo"        # Default: gpt-3.5-turbo
export CHATBOT_MAX_TOKENS="1024"            # Default: 1024
export CHATBOT_TEMPERATURE="0.7"            # Default: 0.7
export CHAT_RATE_LIMIT_PER_MIN="20"        # Default: 20
```

### Configuration in Code

Edit [chatbotana.py](chatbotana.py):

```python
CHATBOT_MODEL = "gpt-4"  # or any OpenRouter supported model
CHATBOT_MAX_TOKENS = 2048
CHATBOT_TEMPERATURE = 0.5
```

## API Reference

### Classes

#### ChatRequest
```python
ChatRequest(message: str, session_id: Optional[str] = None)
```
- `message`: The user's message (max 5000 characters)
- `session_id`: Optional session ID for context continuity

#### ChatResponse
```python
ChatResponse(status: str, response: str, session_id: str)
```
- `status`: "success" or "error"
- `response`: The AI's response text
- `session_id`: The session ID

#### ChatbotSession (internal)
```python
ChatbotSession(session_id: str)
```
Methods:
- `add_message(role, content)`: Add a message to history
- `get_messages()`: Get all messages
- `is_expired(timeout_minutes=30)`: Check if session expired

### Functions

#### send_message
```python
send_message(payload: ChatRequest, client_ip: str = "unknown") -> Dict[str, Any]
```
Sends a message and gets AI response. Includes:
- Input validation
- Rate limiting
- Error handling

#### get_history
```python
get_history(payload: HistoryRequest) -> Dict[str, Any]
```
Returns conversation history with message count.

#### delete_session_handler
```python
delete_session_handler(session_id: str) -> Dict[str, Any]
```
Clears a chat session from memory.

#### analyze_with_context_handler
```python
analyze_with_context_handler(payload: SentimentContextRequest) -> Dict[str, Any]
```
Analyzes comments with AI insights.

## Features

✓ **Session Management** - In-memory conversation tracking
✓ **Rate Limiting** - 20 messages/min per IP (configurable)
✓ **Input Validation** - Message length and format checks
✓ **Error Handling** - Comprehensive error messages
✓ **API Integration** - OpenRouter API support
✓ **Sentiment Analysis** - AI-powered comment analysis
✓ **Logging** - Built-in logging support

## Error Handling

### Common Errors

| Error | Solution |
|-------|----------|
| `Message cannot be empty` | Provide a non-empty message |
| `Message too long` | Keep message under 5000 chars |
| `Rate limit exceeded` | Wait 1 minute before next message |
| `OpenRouter API key not configured` | Set `OPENROUTER_API_KEY` in chatbotana.py |
| `Connection error` | Check internet connection |
| `API timeout` | Try again (30 sec timeout) |

## Testing

Run the comprehensive test suite:

```bash
python test_chatbot.py
```

Tests cover:
- Module imports
- Request/Response models
- Session management
- Rate limiting
- Input validation
- History management

## Frontend Usage

The included HTML/CSS/JS files provide a web interface:

1. Open `chatbot.html` in a browser
2. Type messages in the input field
3. Click send or press Enter
4. View conversation history

Note: HTML interface requires a backend server to handle API requests.

## Production Deployment

For production use:

1. **Use a Database** - Replace in-memory `_chat_sessions` with database
2. **Secure API Key** - Use environment variables or secrets manager
3. **Add Authentication** - Implement user authentication
4. **Monitor Logs** - Set up logging and monitoring
5. **Rate Limiting** - Consider using Redis for distributed rate limiting
6. **HTTPS** - Use HTTPS in production
7. **CORS** - Configure CORS appropriately

## Comparison with orbit-ai-bot

The `orbit-ai-bot` folder contains a **Node.js/Express backend** for insurance product recommendations. The `adimpactbot` folder is a separate **Python chatbot** for:

- Sentiment analysis discussions
- Comment analysis
- Conversational AI
- Session-based interactions

These are independent projects with different purposes:
- **orbit-ai-bot**: Insurance product chatbot (Node.js)
- **adimpactbot**: Sentiment analysis chatbot (Python)

## Dependencies

- `requests` - HTTP requests to OpenRouter API
- Python 3.7+

## Troubleshooting

### Issue: "No module named 'chatbotana'"
**Solution**: Make sure you're running from the `adimpactbot` directory

### Issue: API Key Shows "sk-your-api-key-here"
**Solution**: Replace with your actual OpenRouter API key in chatbotana.py

### Issue: Imports fail
**Solution**: Run from the correct directory:
```bash
cd c:\Users\mohd arif ansari\OneDrive\Desktop\orbit-ai-bot\adimpactbot
python test_chatbot.py
```

### Issue: "Connection error to OpenRouter"
**Solution**: 
- Check internet connection
- Verify API key is valid
- Check OpenRouter API status

## Next Steps

1. Replace API key with your actual key
2. Run tests to verify setup
3. Try the usage examples
4. Integrate with your application
5. Configure for production

## Files Reference

| File | Purpose |
|------|---------|
| `chatbot.py` | Main API and business logic |
| `chatbotana.py` | Core chatbot engine |
| `chatbot.html` | Web UI |
| `chatbot.js` | Frontend interactions |
| `chatbot.css` | Frontend styling |
| `test_chatbot.py` | Test suite |
| `README.md` | Documentation |

## Version

**Version 1.0** - Initial release
- OpenRouter API integration
- Session management
- Rate limiting
- Sentiment analysis support
- Comprehensive testing

## License

Internal use - AdImpact project
