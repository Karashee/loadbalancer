# Makefile for ICS4104 Load Balancer
# Provides convenient targets for building and managing the stack

.PHONY: help build up down clean logs test

# Default target
help:
	@echo "ICS4104 Load Balancer - Makefile Targets"
	@echo "========================================"
	@echo "make build    - Build all Docker images (server + load balancer)"
	@echo "make up       - Start the load balancer stack"
	@echo "make down     - Stop the load balancer stack"
	@echo "make clean    - Stop and remove all containers, networks, and images"
	@echo "make logs     - Show load balancer logs"
	@echo "make test     - Run tests (requires stack to be running)"
	@echo "make status   - Show status of all containers"

# Build all images
build:
	@echo "Building server image..."
	docker build -t server:latest -f Dockerfile .
	@echo ""
	@echo "Building load balancer image..."
	docker build -t load_balancer:latest -f Dockerfile.lb .
	@echo ""
	@echo "✓ Build complete!"

# Start the stack
up:
	@echo "Starting load balancer stack..."
	docker-compose up -d
	@echo ""
	@echo "✓ Stack started!"
	@echo ""
	@echo "Load balancer available at: http://localhost:5000"
	@echo "Check status with: make logs"

# Stop the stack
down:
	@echo "Stopping load balancer stack..."
	docker-compose down
	@echo "✓ Stack stopped!"

# Clean everything
clean:
	@echo "Cleaning up everything..."
	@echo ""
	@echo "Stopping all containers..."
	-docker ps -a --filter "network=net1" --format "{{.Names}}" | xargs -r docker stop 2>/dev/null || true
	@echo ""
	@echo "Removing all containers..."
	-docker ps -a --filter "network=net1" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true
	@echo ""
	@echo "Removing docker-compose stack..."
	-docker-compose down -v 2>/dev/null || true
	@echo ""
	@echo "Removing images..."
	-docker rmi server:latest 2>/dev/null || true
	-docker rmi load_balancer:latest 2>/dev/null || true
	@echo ""
	@echo "Removing network..."
	-docker network rm net1 2>/dev/null || true
	@echo ""
	@echo "✓ Cleanup complete!"

# Show logs
logs:
	@echo "Load Balancer Logs (Ctrl+C to exit):"
	@echo "======================================"
	docker-compose logs -f load_balancer

# Show status
status:
	@echo "Load Balancer Status:"
	@echo "====================="
	@docker ps --filter "name=load_balancer" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Server Replicas:"
	@echo "================"
	@docker ps --filter "network=net1" --filter "name=server" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No server replicas running"

# Run tests
test:
	@echo "Running tests..."
	@echo ""
	@echo "Test 1: Check /rep endpoint"
	@curl -s http://localhost:5000/rep | python -m json.tool
	@echo ""
	@echo "Test 2: Route /home request"
	@curl -s http://localhost:5000/home | python -m json.tool
	@echo ""
	@echo "Test 3: Check container status"
	@make status
