# PowerShell setup script for Docker environment

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Docker Setup for Load Balancer" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build server image
Write-Host "Step 1: Building server image..." -ForegroundColor Yellow
try {
    docker build -t server:latest .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Server image built" -ForegroundColor Green
    } else {
        throw "Docker build failed"
    }
} catch {
    Write-Host "ERROR: Failed to build server image" -ForegroundColor Red
    Write-Host "Make sure Docker Desktop is running" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Step 2: Create Docker network
Write-Host "Step 2: Creating Docker network 'net1'..." -ForegroundColor Yellow
try {
    $networkExists = docker network inspect net1 2>$null
    if ($networkExists) {
        Write-Host "Network 'net1' already exists" -ForegroundColor Yellow
    } else {
        docker network create net1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Network created" -ForegroundColor Green
        } else {
            throw "Network creation failed"
        }
    }
} catch {
    Write-Host "ERROR: Failed to create network" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now run the load balancer:" -ForegroundColor White
Write-Host "  python load_balancer/app.py" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
