# Setup & Deployment Guide - AdImpact Chatbot v2.0

## Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- pip or conda package manager
- OpenRouter API key (get from https://openrouter.ai)

### 2. Clone & Setup

```bash
# Clone repository
git clone <your-repo-url>
cd adimpactbot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# IMPORTANT: Add your OpenRouter API key
nano .env  # or use your preferred editor
```

**Required settings in `.env`:**
```ini
# CRITICAL - Must be set
OPENROUTER_API_KEY=sk_live_xxxxxxxxxx

# Optional - Defaults provided
HOST=0.0.0.0
PORT=8000
CHATBOT_MODEL=gpt-3.5-turbo
CORS_ORIGINS=["http://localhost:8000","http://localhost:3000"]
```

### 4. Run the Server

```bash
# Development mode (with auto-reload)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience scripts:
# Windows:
python main.py
# Linux/macOS:
python main.py
```

### 5. Access the Chatbot

Open your browser to: **http://localhost:8000**

---

## Installation Details

### System Requirements

| Requirement | Requirement |
|---|---|
| Python | 3.8+ |
| Memory | 512MB minimum (1GB recommended) |
| Disk Space | 500MB for dependencies |
| Network | Internet required for OpenRouter API |

### Virtual Environment Setup

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### Verify Installation

```bash
# Check all packages installed
pip list

# Verify FastAPI
python -c "import fastapi; print(f'✓ FastAPI {fastapi.__version__}')"

# Verify Uvicorn
python -c "import uvicorn; print(f'✓ Uvicorn {uvicorn.__version__}')"

# Verify Pydantic
python -c "import pydantic; print(f'✓ Pydantic {pydantic.__version__}')"
```

---

## Configuration

### Environment Variables

All configuration is done through `.env` file. See `.env.example` for all options.

#### Essential Variables

```ini
# API Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
CHATBOT_MODEL=gpt-3.5-turbo

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=["http://localhost:8000"]
ALLOWED_HOSTS=["localhost","127.0.0.1"]

# Rate Limiting
CHAT_RATE_LIMIT_PER_MIN=20
```

### Getting an OpenRouter API Key

1. Visit https://openrouter.ai
2. Sign up for a free account
3. Go to API Keys section
4. Generate a new key
5. Copy the key to your `.env` file

```ini
OPENROUTER_API_KEY=sk_live_YOUR_KEY_HERE
```

---

## Development

### Enable Debug Mode

```ini
# .env
DEBUG=true
LOG_LEVEL=DEBUG
RELOAD=true
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific file
pytest tests/test_chatbot.py

# Run specific test
pytest tests/test_chatbot.py::test_send_message
```

### Code Quality

```bash
# Format code with Black
black .

# Check linting
flake8 .

# Type checking
mypy .

# Sort imports
isort .
```

### API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

---

## Deployment

### Production Recommendations

#### Environment Setup
```bash
# Use production environment
ENVIRONMENT=production
DEBUG=false
RELOAD=false
LOG_LEVEL=WARNING
```

#### Security Settings
```bash
# HTTPS/TLS
SECURE_COOKIES=true

# Restrict CORS to your domain
CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com"]

# Strong API key
OPENROUTER_API_KEY=sk_live_very_long_key
```

### Using Uvicorn in Production

```bash
# With Gunicorn (Unix/Linux/macOS)
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

# With Systemd (Linux)
# Create /etc/systemd/system/adimpact.service
[Unit]
Description=AdImpact Chatbot
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/user/adimpactbot
Environment="PATH=/home/user/adimpactbot/venv/bin"
ExecStart=/home/user/adimpactbot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl start adimpact
sudo systemctl enable adimpact
sudo systemctl status adimpact
```

### Using Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV OPENROUTER_API_KEY=""
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build image
docker build -t adimpact-chatbot:2.0 .

# Run container
docker run -d \
  --name adimpact \
  -p 8000:8000 \
  -e OPENROUTER_API_KEY=sk_live_xxxxx \
  adimpact-chatbot:2.0

# Check logs
docker logs -f adimpact
```

### Using Cloud Platforms

#### Heroku
```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port $PORT" > Procfile

# Deploy
heroku create adimpact-chatbot
git push heroku main
heroku config:set OPENROUTER_API_KEY=sk_live_xxxxx
```

#### AWS (Lambda - requires adjustments)
- Use API Gateway + Lambda layer with FastAPI adapter
- Store secrets in Secrets Manager
- Use DynamoDB for session storage

#### Google Cloud Run
```bash
# Deploy directly
gcloud run deploy adimpact-chatbot \
  --source . \
  --port 8000 \
  --set-env-vars OPENROUTER_API_KEY=sk_live_xxxxx
```

#### Azure App Service
```bash
# Deployment using .zip
az webapp deployment source config-zip \
  -r <resource-group> \
  -n <app-name> \
  --src <path-to-zip>
```

---

## Monitoring & Logging

### Real-time Logs

```bash
# Tail logs in real-time
tail -f logs.log

# Watch specific log level
grep "ERROR" logs.log
```

### Health Check

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2024-01-06T10:30:00","version":"2.0.0"}
```

### Performance Monitoring

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep uvicorn'

# Monitor with htop
htop -p $(pgrep -f uvicorn)
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
# Ensure virtual environment is active
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "OpenRouter API key is not configured"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify API key is set
grep OPENROUTER_API_KEY .env

# Make sure .env is loaded
python -c "from main import settings; print(settings.openrouter_api_key[:10])"
```

### Issue: "Connection refused" when accessing http://localhost:8000

**Solution:**
```bash
# Verify server is running
ps aux | grep uvicorn

# Check port is available
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Try different port
python -m uvicorn main:app --port 8080
```

### Issue: CORS errors in browser console

**Solution:**
```ini
# Update .env
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

Then restart server.

### Issue: API rate limiting

**Solution:**
```ini
# Increase rate limit in .env
CHAT_RATE_LIMIT_PER_MIN=50
```

---

## Upgrading

### From v1.0 to v2.0

```bash
# 1. Backup current installation
cp -r adimpactbot adimpactbot.backup

# 2. Pull new version
git pull

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Review new environment variables
diff .env.example .env

# 5. Add any missing variables to .env

# 6. Restart server
python main.py
```

---

## Support & Help

### Documentation
- API Docs: http://localhost:8000/api/docs
- Security Guide: [SECURITY.md](SECURITY.md)
- Improvements: [README.md](README.md)

### Common URLs
- **Chatbot UI:** http://localhost:8000
- **API Endpoint:** http://localhost:8000/api/chat/message
- **Health Check:** http://localhost:8000/health

### Getting Help
- Check error logs: `grep ERROR logs.log`
- Review `.env` configuration
- Check OpenRouter API status
- Review [SECURITY.md](SECURITY.md) for security issues
