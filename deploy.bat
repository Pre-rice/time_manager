@echo off
chcp 65001 >nul
title Time Manager - 开发模式
echo ========================================
echo   Time Manager - 开发模式
echo ========================================
echo.

:: ===== 步骤 1: 启动 Docker =====
echo [1/5] 启动 Docker 容器...
cd /d e:\编程\time_manager\backend
docker compose up -d >nul 2>&1
echo   -- Docker 容器正常

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
    echo   失败！请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)
echo   -- 后端已重启 (http://localhost:8000)

:: ===== 步骤 4: 编译前端 =====
echo.
echo [4/5] 编译前端(debug模式,比release快30%)...
cd /d e:\编程\time_manager\frontend
call D:\Flutter\bin\flutter.bat build web --debug
if not exist e:\编程\time_manager\frontend\build\web\index.html (
    echo   编译失败
    pause
    exit /b 1
)
echo   -- 编译完成

:: ===== 步骤 5: 启动 HTTP 服务器 =====
echo.
echo [5/5] 启动 HTTP 服务器(端口 8080)...
for /f "tokens=2 delims= " %%a in ('tasklist ^| findstr /i "python" ^| findstr "http.server"') do (
    taskkill /f /pid %%a >nul 2>&1
)
start /B python -m http.server 8080 -d e:\编程\time_manager\frontend\build\web
echo   -- 前端: http://localhost:8080
echo   -- 后端: http://localhost:8000
echo.
echo   改代码后需重新运行此脚本
echo   如需更快: 下次手动先 flutter build web --debug 再启动 http 即可
echo.
pause