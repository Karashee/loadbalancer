@echo off
REM Batch script alternative to Makefile for Windows
REM Usage: Makefile.bat <target>

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="build" goto build
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="clean" goto clean
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="test" goto test
goto help

:help
echo ICS4104 Load Balancer - Build Targets
echo ========================================
echo Makefile.bat build    - Build all Docker images
echo Makefile.bat up       - Start the load balancer stack
echo Makefile.bat down     - Stop the load balancer stack
echo Makefile.bat clean    - Stop and remove everything
echo Makefile.bat logs     - Show load balancer logs
echo Makefile.bat status   - Show status of all containers
echo Makefile.bat test     - Run tests
goto end

:build
echo Building server image...
docker build -t server:latest -f Dockerfile .
echo.
echo Building load balancer image...
docker build -t load_balancer:latest -f Dockerfile.lb .
echo.
echo Build complete!
goto end

:up
echo Starting load balancer stack...
docker-compose up -d
echo.
echo Stack started!
echo.
echo Load balancer available at: http://localhost:5000
echo Check status with: Makefile.bat logs
goto end

:down
echo Stopping load balancer stack...
docker-compose down
echo Stack stopped!
goto end

:clean
echo Cleaning up everything...
echo.
echo Stopping all containers...
for /f "tokens=*" %%i in ('docker ps -a --filter "network=net1" --format "{{.Names}}"') do docker stop %%i 2>nul
echo.
echo Removing all containers...
for /f "tokens=*" %%i in ('docker ps -a --filter "network=net1" --format "{{.Names}}"') do docker rm %%i 2>nul
echo.
echo Removing docker-compose stack...
docker-compose down -v 2>nul
echo.
echo Removing images...
docker rmi server:latest 2>nul
docker rmi load_balancer:latest 2>nul
echo.
echo Removing network...
docker network rm net1 2>nul
echo.
echo Cleanup complete!
goto end

:logs
echo Load Balancer Logs (Ctrl+C to exit):
echo ======================================
docker-compose logs -f load_balancer
goto end

:status
echo Load Balancer Status:
echo =====================
docker ps --filter "name=load_balancer" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
echo Server Replicas:
echo ================
docker ps --filter "network=net1" --filter "name=server" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>nul
if errorlevel 1 echo No server replicas running
goto end

:test
echo Running tests...
echo.
echo Test 1: Check /rep endpoint
curl -s http://localhost:5000/rep
echo.
echo.
echo Test 2: Route /home request
curl -s http://localhost:5000/home
echo.
echo.
echo Test 3: Check container status
call :status
goto end

:end
