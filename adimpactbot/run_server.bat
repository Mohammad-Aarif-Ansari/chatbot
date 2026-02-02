@echo off
REM Start AdImpact Chatbot FastAPI server

echo Starting AdImpact Chatbot Server...
echo.
echo The chatbot will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.

REM Run uvicorn server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
