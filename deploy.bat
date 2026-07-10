@echo off
chcp 65001 >nul
title Time Manager - 开发模式
echo ========================================
echo   Time Manager - 开发模式
echo ========================================
echo.

:: ===== 步骤 1: 启动 Docker =====
echo [1/4] 启动 Docker 容器...
cd /d e:\编程\time_manager\backend
docker compose up -d >nul 2>&1
echo   -- Docker 容器正常

:: ===== 步骤 2: 迁移数据库 =====
echo [2/4] 迁移数据库...
docker exec backend-api-1 pip install psycopg2-binary -q >nul 2>&1
docker cp e:\编程\time_manager\deploy_migrate.py backend-api-1:/tmp/deploy_migrate.py >nul 2>&1
docker exec backend-api-1 python /tmp/deploy_migrate.py 2>&1
echo.

:: ===== 步骤 3: 重启后端 =====
echo [3/4] 重启后端 API...
docker restart backend-api-1 >nul 2>&1
if %errorlevel% neq 0 (
    echo   失败！请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)
echo   -- 后端已重启 (http://localhost:8000)

:: ===== 步骤 4: 启动前端开发服务器 =====
echo.
echo [4/4] 启动前端开发服务器...
echo   首次编译约 20-30 秒，浏览器打开 http://localhost:8080 即可
echo   改代码后按 r 键热重载，或直接刷新浏览器
echo.
cd /d e:\编程\time_manager\frontend
call D:\Flutter\bin\flutter.bat run -d web-server --web-port 8080

echo.
echo   前端进程已结束
pause