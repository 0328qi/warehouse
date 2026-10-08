@echo off
REM 一键启动开发环境：后端 8000 + 前端 5173
start "WMS-Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload"
start "WMS-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 5 >nul
start http://localhost:5173
