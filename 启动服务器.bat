@echo off
echo ========================================
echo   Starting Server...
echo ========================================
echo.
echo Checking dependencies...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [ERROR] Flask not installed, installing...
    pip install flask
)
echo.
echo Server started successfully!
echo Please visit: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.
python server.py
pause
