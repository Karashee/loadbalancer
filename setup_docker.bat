@echo off
REM Setup script for Docker environment

echo ====================================
echo Docker Setup for Load Balancer
echo ====================================
echo.

echo Step 1: Building server image...
docker build -t server:latest .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build server image
    echo Make sure Docker Desktop is running
    pause
    exit /b 1
)
echo SUCCESS: Server image built
echo.

echo Step 2: Creating Docker network 'net1'...
docker network inspect net1 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Network 'net1' already exists
) else (
    docker network create net1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create network
        pause
        exit /b 1
    )
    echo SUCCESS: Network created
)
echo.

echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo You can now run the load balancer:
echo   python load_balancer/app.py
echo.
pause
