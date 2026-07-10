@echo off
chcp 65001 >nul
title Time Manager 一键部署
echo ========================================
echo   Time Manager - 一键部署
echo ========================================
echo.

:: ===== 步骤 1: 启动 Docker =====
echo [1/5] 启动 Docker 容器...
cd /d e:\编程\time_manager\backend
docker compose up -d >nul 2>&1
echo   ✅ Docker 容器正常

:: ===== 步骤 2: 迁移数据库 =====
echo [2/5] 迁移数据库...
docker exec backend-api-1 pip install psycopg2-binary -q >nul 2>&1
docker cp e:\编程\time_manager\deploy_migrate.py backend-api-1:/tmp/deploy_migrate.py >nul 2>&1
docker exec backend-api-1 python /tmp/deploy_migrate.py 2>&1
echo.

:: ===== 步骤 3: 重启后端 =====
echo [3/5] 重启后端 API...
docker restart backend-api-1 >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ 失败！请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)
echo   ✅ 后端已重启 (http://localhost:8000)
timeout /t 3 /nobreak >nul

:: ===== 步骤 4: 构建前端 =====
echo [4/5] 构建前端...
cd /d e:\编程\time_manager\frontend
D:\Flutter\bin\flutter.bat build web --release >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ 前端构建失败
    pause
    exit /b 1
)
echo   ✅ 前端构建完成

:: ===== 步骤 5: 启动 HTTP 服务器 =====
echo [5/5] 启动 HTTP 服务器（端口 8080）...
for /f "tokens=2 delims= " %%a in ('tasklist ^| findstr /i "python" ^| findstr "http.server"') do (
    taskkill /f /pid %%a >nul 2>&1
)
start /B python -m http.server 8080 -d e:\编程\time_manager\frontend\build\web
echo   ✅ 服务器已启动

echo.
echo ========================================
echo   🎉 部署完成！
echo   前端: http://localhost:8080
echo   后端: http://localhost:8000
echo ========================================
pause >nul