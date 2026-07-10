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
    echo   -- 失败！请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)
echo   -- 后端已重启 (http://localhost:8000)
timeout /t 3 /nobreak >nul

:: ===== 步骤 4: 启动前端开发服务器 =====
echo [4/4] 启动前端开发服务器（支持热重载）...
echo   首次编译约 20-30 秒，之后改代码刷浏览器即可
start "FlutterDev" /D e:\编程\time_manager\frontend D:\Flutter\bin\flutter.bat run -d web-server --web-port 8080
echo   -- 前端开发服务器已启动 (http://localhost:8080)
echo   注意: 请在新打开的窗口中查看编译进度
echo.

echo ========================================
echo   部署完成！
echo   前端: http://localhost:8080 (支持热重载)
echo   后端: http://localhost:8000
echo.
echo   关闭方式: 按 Ctrl+C 停止 flutter 进程
echo   如需发布: 运行 flutter build web --release
echo ========================================
pause >nul