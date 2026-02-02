@echo off
REM Start the AdImpact Chatbot FastAPI backend

echo Starting AdImpact Chatbot API...
echo.
echo Step 1: Installing dependencies
pip install -r requirements.txt
echo.
echo Step 2: Starting FastAPI server
echo.
echo The server will start at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
