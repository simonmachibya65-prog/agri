@echo off
title Smart Crop AI Server
echo.
echo  ==========================================
echo   Smart Crop AI - Starting Server...
echo  ==========================================
echo.
echo  URL: http://localhost:8000
echo  Login: demo / demo123
echo.
echo  Press Ctrl+C to stop the server
echo.
C:\Users\simon\anaconda3\envs\ai_gpu\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
