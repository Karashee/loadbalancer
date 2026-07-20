# ICS4104 Load Balancer

A distributed load balancer implementation with consistent hashing.

Group Members:
Joy Cherutich - 157463
Andrew Karanja - 167144
Zahra Isiaho - 169652

## Quick Start

### Using Make (Linux/Mac/Git Bash)

```bash
# Build images
make build

# Start the stack
make up

# Check status
make status

# View logs
make logs

# Stop the stack
make down

# Clean everything
make clean
```

### Using Batch Script (Windows CMD)

```cmd
REM Build images
Makefile.bat build

REM Start the stack
Makefile.bat up

REM Check status
Makefile.bat status

REM View logs
Makefile.bat logs

REM Stop the stack
Makefile.bat down

REM Clean everything
Makefile.bat clean
```

### Using Docker Compose Directly

```bash
# Build and start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

## Project Structure

```
ics4104-load-balancer/
├── server/           # Flask web server implementation
├── load_balancer/    # Load balancer logic
├── hashing/          # Consistent hashing implementation
├── tests/            # Unit and integration tests
├── scripts/          # Utility scripts
├── results/          # Performance test results
├── docker-compose.yml
├── Makefile
├── README.md
└── requirements.txt
```

## Getting Started

### Build the Server Image

```bash
docker build -t server:latest .
```

### Run a Server Instance

```bash
docker run -e SERVER_ID=1 -p 5000:5000 server:latest
```

### Test Endpoints

```bash
# Test home endpoint
curl localhost:5000/home

# Test heartbeat endpoint
curl localhost:5000/heartbeat
```

## Server Endpoints

- `GET /home` - Returns server identification message
- `GET /heartbeat` - Health check endpoint (returns HTTP 200)

## Load Balancer

### Requirements

- Python 3.11+
- Flask (installed via requirements.txt)
- Docker (for container management)
- Docker Compose (for stack orchestration)

### Stack Architecture

The complete system runs in Docker containers:

```
Docker Compose Stack
├── Load Balancer Container (privileged, port 5000)
│   ├── Docker socket mounted (/var/run/docker.sock)
│   ├── Can spawn/kill server containers
│   └── Manages consistent hash ring
└── Server Replicas (spawned dynamically on net1)
    ├── server-1, server-2, server-3... (initial)
    └── Auto-respawned on failure
```

### Running the Load Balancer

```bash
# Install dependencies
pip install -r requirements.txt

# Build server image
docker build -t server:latest .

# Create Docker network
docker network create net1

# Run load balancer
python load_balancer/app.py
```

The load balancer starts on port 5000 by default with 3 pre-seeded replicas.

### Load Balancer Endpoints

- `GET /rep` - Returns replica information (count and hostnames)
- `POST /add` - Add new replica servers with Docker container spawning
  - Payload: `{"n": int, "hostnames": [...]}`
- `DELETE /rm` - Remove replica servers and stop containers
  - Payload: `{"n": int, "hostnames": [...]}`
- `GET /<path>` - Catch-all route that proxies requests to backend replicas
  - Uses consistent hashing to select target server
  - Returns backend response or error if endpoint doesn't exist

### Features

- **Consistent Hashing**: Requests distributed using consistent hash ring with 9 virtual nodes per server
- **Request Proxying**: All GET/POST/PUT/DELETE requests to unknown paths are routed to backend servers
- **Health Monitoring**: Background thread checks each replica every 5 seconds via /heartbeat endpoint
- **Auto-Respawn**: Failed replicas are automatically replaced with new containers maintaining target count N
- **Load Distribution**: Requests distributed across replicas based on path hashing

### Testing

```bash
# Test replica info
curl http://localhost:5000/rep

# Test request routing
curl http://localhost:5000/home

# Test health check endpoint
curl http://localhost:5000/heartbeat

# Test non-existent endpoint (should return 400)
curl http://localhost:5000/invalid

# Test add endpoint
curl -X POST http://localhost:5000/add -H "Content-Type: application/json" -d "{\"n\": 2, \"hostnames\": [\"server-4\", \"server-5\"]}"

# Test remove endpoint
curl -X DELETE http://localhost:5000/rm -H "Content-Type: application/json" -d "{\"n\": 1, \"hostnames\": [\"server-4\"]}"

# Run automated tests
python scripts/test_load_balancer.py
python scripts/test_add_rm.py
python scripts/test_routing.py

# Run load tests and analyses
python scripts/analysis_1_distribution.py  # A-1: Distribution test (N=3, 10K requests)
python scripts/analysis_2_scalability.py   # A-2: Scalability test (N=2-6, 10K each)

# Or use make/batch
make test          # Linux/Mac
Makefile.bat test  # Windows
```

### Load Testing & Performance Analysis

**Analysis 1: Load Distribution (N=3)**

- Sends 10,000 async requests to /home
- Measures distribution across 3 replicas
- Generates bar chart: `results/a1_distribution.png`

**Analysis 2: Scalability (N=2 to N=6)**

- Tests with 2, 3, 4, 5, and 6 replicas
- Sends 10,000 requests per configuration
- Generates line chart: `results/a2_scalability.png`

```bash
# Run analysis 1
python scripts/analysis_1_distribution.py

# Run analysis 2
python scripts/analysis_2_scalability.py

# View results
start results\a1_distribution.png   # Windows
open results/a1_distribution.png    # Mac
xdg-open results/a1_distribution.png # Linux
```

### Auto-Respawn Testing

```bash
# 1. Check current replicas
curl http://localhost:5000/rep

# 2. Kill a container
docker kill server-1

# 3. Wait 5-10 seconds, then check again
curl http://localhost:5000/rep
docker ps --filter network=net1

# Expected: New container with random name appears, N maintained
```

## Documentation

- **[README.md](README.md)** - This file (quick start and usage)


- **Analysis Results** - See `results/` directory for charts:
  - `a1_distribution.png` - Load distribution test
  - `a2_scalability.png` - Scalability analysis
  - `a3_recovery.png` - Failure recovery timeline
  - `a4_hash_comparison_distribution.png` - Hash function comparison
  - `a4_hash_comparison_scalability.png` - Hash scaling comparison
