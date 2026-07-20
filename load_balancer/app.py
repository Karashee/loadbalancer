"""
Load Balancer Flask application with consistent hashing.

Manages replica servers and routes requests using consistent hash ring.
"""
import os
import sys
import subprocess
import random
import string
import threading
import time
import requests
from typing import List, Dict, Optional, Tuple
from flask import Flask, jsonify, request as flask_request, Response

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing.consistent_hash import ConsistentHashMap


class LoadBalancer:
    """
    Load balancer with consistent hashing for replica management.
    
    Attributes:
        hash_map: Consistent hash map for request routing
        replicas: Dictionary mapping server IDs to hostnames
        next_server_id: Counter for generating unique server IDs
        network_name: Docker network name for servers
        mock_mode: If True, skip actual Docker operations
    """
    
    def __init__(self, network_name: str = "net1", mock_mode: bool = False):
        """Initialize load balancer with empty replica registry."""
        self.hash_map = ConsistentHashMap()
        self.replicas: Dict[int, str] = {}
        self.next_server_id = 1
        self.network_name = network_name
        self.mock_mode = mock_mode
        self.target_replica_count = 3  # Target N to maintain
        self.heartbeat_interval = 5  # seconds between health checks
        self.heartbeat_timeout = 2  # seconds to wait for response
        self.health_check_thread = None
        self.running = False
        self.lock = threading.Lock()  # Thread-safe operations
    
    def add_replica(self, server_id: int, hostname: str, spawn_container: bool = True) -> None:
        """
        Add a replica server to the load balancer.
        
        Args:
            server_id: Unique server identifier
            hostname: Server hostname or container name
            spawn_container: Whether to spawn a Docker container
            
        Raises:
            ValueError: If server already exists
            RuntimeError: If container spawn fails
        """
        if server_id in self.replicas:
            raise ValueError(f"Replica {server_id} already exists")
        
        # Spawn Docker container if requested
        if spawn_container:
            success = self._spawn_container(server_id, hostname)
            if not success:
                raise RuntimeError(f"Failed to spawn container for {hostname}")
        
        self.hash_map.add_server(server_id)
        self.replicas[server_id] = hostname
        
        # Update next_server_id if needed
        if server_id >= self.next_server_id:
            self.next_server_id = server_id + 1
    
    def remove_replica(self, server_id: int, stop_container: bool = True) -> None:
        """
        Remove a replica server from the load balancer.
        
        Args:
            server_id: Server identifier to remove
            stop_container: Whether to stop and remove the Docker container
            
        Raises:
            ValueError: If server does not exist
        """
        if server_id not in self.replicas:
            raise ValueError(f"Replica {server_id} does not exist")
        
        hostname = self.replicas[server_id]
        
        # Stop and remove Docker container if requested
        if stop_container:
            self._stop_container(hostname)
        
        self.hash_map.remove_server(server_id)
        del self.replicas[server_id]
    
    def get_replica_count(self) -> int:
        """
        Get the number of active replicas.
        
        Returns:
            Number of replicas
        """
        return len(self.replicas)
    
    def get_replica_hostnames(self) -> List[str]:
        """
        Get list of all replica hostnames.
        
        Returns:
            Sorted list of hostnames
        """
        return [self.replicas[sid] for sid in sorted(self.replicas.keys())]
    
    def route_request(self, request_id: int) -> Optional[str]:
        """
        Route a request to a replica using consistent hashing.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Hostname of the selected replica, or None if no replicas available
        """
        server_id = self.hash_map.get_server(request_id)
        if server_id is None:
            return None
        return self.replicas.get(server_id)
    
    def get_server_id_by_hostname(self, hostname: str) -> Optional[int]:
        """
        Find server ID by hostname.
        
        Args:
            hostname: Server hostname to search for
            
        Returns:
            Server ID if found, None otherwise
        """
        for server_id, h in self.replicas.items():
            if h == hostname:
                return server_id
        return None
    
    def _generate_random_hostname(self) -> str:
        """
        Generate a random hostname for unnamed server slots.
        
        Returns:
            Random hostname in format "server-XXXXX"
        """
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        return f"server-{random_suffix}"
    
    def _spawn_container(self, server_id: int, hostname: str) -> bool:
        """
        Spawn a Docker container for a server replica.
        
        Args:
            server_id: Server identifier
            hostname: Container hostname/name
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            print(f"[MOCK] Would spawn container: {hostname} (SERVER_ID={server_id})")
            return True
        
        try:
            # Docker run command
            cmd = [
                "docker", "run",
                "-d",  # Detached mode
                "--name", hostname,
                "--network", self.network_name,
                "--network-alias", hostname,
                "-e", f"SERVER_ID={server_id}",
                "server:latest"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✓ Spawned container: {hostname} (SERVER_ID={server_id})")
                return True
            else:
                print(f"✗ Failed to spawn container {hostname}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout spawning container {hostname}")
            return False
        except FileNotFoundError:
            print(f"✗ Docker not found. Install Docker or run in mock mode (MOCK_MODE=1)")
            return False
        except Exception as e:
            print(f"✗ Error spawning container {hostname}: {e}")
            return False
    
    def start_health_checks(self):
        """Start background health check thread."""
        if self.health_check_thread is not None:
            return  # Already running
        
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        print("✓ Health check thread started")
    
    def stop_health_checks(self):
        """Stop background health check thread."""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        print("✓ Health check thread stopped")
    
    def _health_check_loop(self):
        """Background loop for health checking replicas."""
        while self.running:
            time.sleep(self.heartbeat_interval)
            self._check_all_replicas()
    
    def _check_all_replicas(self):
        """Check health of all replicas and respawn failed ones."""
        with self.lock:
            failed_servers = []
            
            # Check each replica
            for server_id, hostname in list(self.replicas.items()):
                if not self._check_replica_health(hostname):
                    print(f"⚠️  Replica {hostname} (ID={server_id}) failed health check")
                    failed_servers.append((server_id, hostname))
            
            # Respawn failed servers
            for server_id, hostname in failed_servers:
                self._respawn_replica(server_id, hostname)
    
    def _check_replica_health(self, hostname: str) -> bool:
        """
        Check if a replica is healthy via /heartbeat endpoint.
        
        Args:
            hostname: Replica hostname to check
            
        Returns:
            True if healthy, False otherwise
        """
        if self.mock_mode:
            # In mock mode, always return healthy
            return True
        
        try:
            url = f"http://{hostname}:5000/heartbeat"
            response = requests.get(url, timeout=self.heartbeat_timeout)
            return response.status_code == 200
        except Exception:
            return False
    
    def _respawn_replica(self, server_id: int, old_hostname: str):
        """
        Respawn a failed replica with a new random hostname.
        
        Args:
            server_id: Server ID of failed replica
            old_hostname: Hostname of failed replica
        """
        print(f"🔄 Respawning replica {old_hostname} (ID={server_id})")
        
        try:
            # Remove failed replica
            self.remove_replica(server_id, stop_container=True)
            
            # Generate new hostname
            new_hostname = self._generate_random_hostname()
            
            # Add new replica
            new_server_id = self.next_server_id
            self.add_replica(new_server_id, new_hostname, spawn_container=True)
            
            print(f"✓ Respawned as {new_hostname} (ID={new_server_id})")
            
        except Exception as e:
            print(f"✗ Failed to respawn replica: {e}")
    
    def route_to_replica(self, path: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Route a request to a replica using consistent hashing.
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (hostname, server_id) or (None, None) if no replicas
        """
        if not self.replicas:
            return None, None
        
        # Generate request ID from path (simple hash)
        request_id = hash(path) % (2**31)
        
        server_id = self.hash_map.get_server(request_id)
        if server_id is None:
            return None, None
        
        hostname = self.replicas.get(server_id)
        return hostname, server_id
    
    def _stop_container(self, hostname: str) -> bool:
        """
        Stop and remove a Docker container.
        
        Args:
            hostname: Container name to stop
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            print(f"[MOCK] Would stop/remove container: {hostname}")
            return True
        
        try:
            # Stop container
            stop_result = subprocess.run(
                ["docker", "stop", hostname],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Remove container
            rm_result = subprocess.run(
                ["docker", "rm", hostname],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if stop_result.returncode == 0 and rm_result.returncode == 0:
                print(f"✓ Removed container: {hostname}")
                return True
            else:
                print(f"✗ Failed to remove container {hostname}")
                return False
                
        except FileNotFoundError:
            print(f"✗ Docker not found. Install Docker or run in mock mode (MOCK_MODE=1)")
            return False
        except Exception as e:
            print(f"✗ Error removing container {hostname}: {e}")
            return False


# Initialize Flask app and load balancer
app = Flask(__name__)

# Check for mock mode from environment variable
mock_mode = os.environ.get('MOCK_MODE', '0') == '1'
load_balancer = LoadBalancer(mock_mode=mock_mode)

if mock_mode:
    print("\n⚠️  Running in MOCK MODE - Docker operations will be simulated\n")


def ensure_docker_network():
    """Ensure Docker network exists for load balancer."""
    if load_balancer.mock_mode:
        print(f"[MOCK] Would create Docker network: {load_balancer.network_name}")
        return
    
    try:
        # Check if network exists
        result = subprocess.run(
            ["docker", "network", "inspect", load_balancer.network_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Create network
            create_result = subprocess.run(
                ["docker", "network", "create", load_balancer.network_name],
                capture_output=True,
                text=True
            )
            if create_result.returncode == 0:
                print(f"✓ Created Docker network: {load_balancer.network_name}")
            else:
                print(f"✗ Failed to create network: {create_result.stderr}")
        else:
            print(f"✓ Docker network exists: {load_balancer.network_name}")
            
    except FileNotFoundError:
        print(f"✗ Docker not found. Install Docker or set MOCK_MODE=1")
    except Exception as e:
        print(f"✗ Error checking Docker network: {e}")


def seed_replicas():
    """Seed the load balancer with initial replica servers."""
    # Add 3 initial replicas (spawn containers if not in mock mode)
    initial_replicas = [
        (1, "server-1"),
        (2, "server-2"),
        (3, "server-3"),
    ]
    
    spawn_containers = not load_balancer.mock_mode
    
    for server_id, hostname in initial_replicas:
        try:
            load_balancer.add_replica(server_id, hostname, spawn_container=spawn_containers)
        except Exception as e:
            print(f"Warning: Failed to add replica {hostname}: {e}")
    
    # Set target count
    load_balancer.target_replica_count = len(initial_replicas)
    
    mode_str = "with containers" if spawn_containers else "in-memory only"
    print(f"Seeded {len(initial_replicas)} replicas ({mode_str})")


@app.route('/rep', methods=['GET'])
def get_replicas():
    """
    Get replica server information.
    
    Returns:
        JSON response with replica count and hostnames
    """
    replica_count = load_balancer.get_replica_count()
    replica_hostnames = load_balancer.get_replica_hostnames()
    
    return jsonify({
        "message": {
            "N": replica_count,
            "replicas": replica_hostnames
        },
        "status": "successful"
    }), 200


@app.route('/add', methods=['POST'])
def add_replicas():
    """
    Add new replica servers.
    
    Expects JSON payload: {"n": int, "hostnames": [str, ...]}
    - n: Number of replicas to add
    - hostnames: Optional list of hostnames (can be empty or partial)
    
    Returns:
        JSON response with updated replica information or error
    """
    try:
        data = flask_request.get_json()
        
        if not data or 'n' not in data:
            return jsonify({
                "message": "<Error> Missing 'n' parameter",
                "status": "failure"
            }), 400
        
        n = data['n']
        hostnames = data.get('hostnames', [])
        
        # Validate n is positive
        if not isinstance(n, int) or n <= 0:
            return jsonify({
                "message": "<Error> 'n' must be a positive integer",
                "status": "failure"
            }), 400
        
        # Check hostname list length
        if len(hostnames) > n:
            return jsonify({
                "message": "<Error> Length of hostname list is more than newly added instances",
                "status": "failure"
            }), 400
        
        # Generate random hostnames for unnamed slots
        while len(hostnames) < n:
            hostnames.append(load_balancer._generate_random_hostname())
        
        # Add replicas
        added_servers = []
        with load_balancer.lock:
            for hostname in hostnames[:n]:
                server_id = load_balancer.next_server_id
                try:
                    load_balancer.add_replica(server_id, hostname, spawn_container=True)
                    added_servers.append((server_id, hostname))
                except Exception as e:
                    # Rollback: remove successfully added servers
                    for sid, _ in added_servers:
                        load_balancer.remove_replica(sid, stop_container=True)
                    
                    return jsonify({
                        "message": f"<Error> Failed to add replica {hostname}: {str(e)}",
                        "status": "failure"
                    }), 500
            
            # Update target count
            load_balancer.target_replica_count = load_balancer.get_replica_count()
        
        # Return updated replica information
        return jsonify({
            "message": {
                "N": load_balancer.get_replica_count(),
                "replicas": load_balancer.get_replica_hostnames()
            },
            "status": "successful"
        }), 200
        
    except Exception as e:
        return jsonify({
            "message": f"<Error> {str(e)}",
            "status": "failure"
        }), 500


@app.route('/rm', methods=['DELETE'])
def remove_replicas():
    """
    Remove replica servers.
    
    Expects JSON payload: {"n": int, "hostnames": [str, ...]}
    - n: Number of replicas to remove
    - hostnames: Optional list of hostnames to remove (can be empty or partial)
    
    Returns:
        JSON response with updated replica information or error
    """
    try:
        data = flask_request.get_json()
        
        if not data or 'n' not in data:
            return jsonify({
                "message": "<Error> Missing 'n' parameter",
                "status": "failure"
            }), 400
        
        n = data['n']
        hostnames = data.get('hostnames', [])
        
        # Validate n is positive
        if not isinstance(n, int) or n <= 0:
            return jsonify({
                "message": "<Error> 'n' must be a positive integer",
                "status": "failure"
            }), 400
        
        # Check hostname list length
        if len(hostnames) > n:
            return jsonify({
                "message": "<Error> Length of hostname list is more than removable instances",
                "status": "failure"
            }), 400
        
        with load_balancer.lock:
            # Check if we have enough replicas to remove
            current_count = load_balancer.get_replica_count()
            if n > current_count:
                return jsonify({
                    "message": f"<Error> Cannot remove {n} replicas, only {current_count} available",
                    "status": "failure"
                }), 400
            
            # Build list of server IDs to remove
            server_ids_to_remove = []
            
            # First, add explicitly named hostnames
            for hostname in hostnames:
                server_id = load_balancer.get_server_id_by_hostname(hostname)
                if server_id is None:
                    return jsonify({
                        "message": f"<Error> Hostname '{hostname}' not found",
                        "status": "failure"
                    }), 400
                server_ids_to_remove.append(server_id)
            
            # Fill remaining slots with random selection
            remaining_servers = [sid for sid in load_balancer.replicas.keys() 
                               if sid not in server_ids_to_remove]
            
            slots_to_fill = n - len(server_ids_to_remove)
            if slots_to_fill > 0:
                random_selections = random.sample(remaining_servers, slots_to_fill)
                server_ids_to_remove.extend(random_selections)
            
            # Remove replicas
            for server_id in server_ids_to_remove:
                load_balancer.remove_replica(server_id, stop_container=True)
            
            # Update target count
            load_balancer.target_replica_count = load_balancer.get_replica_count()
        
        # Return updated replica information
        return jsonify({
            "message": {
                "N": load_balancer.get_replica_count(),
                "replicas": load_balancer.get_replica_hostnames()
            },
            "status": "successful"
        }), 200
        
    except Exception as e:
        return jsonify({
            "message": f"<Error> {str(e)}",
            "status": "failure"
        }), 500


@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def route_request(path):
    """
    Catch-all route handler that proxies requests to backend replicas.
    
    Uses consistent hashing to select a replica based on the request path.
    
    Args:
        path: Request path
        
    Returns:
        Proxied response from backend server or error
    """
    # Route request to replica
    hostname, server_id = load_balancer.route_to_replica(path)
    
    if hostname is None:
        return jsonify({
            "message": "<Error> No replicas available",
            "status": "failure"
        }), 503
    
    # Build target URL
    target_url = f"http://{hostname}:5000/{path}"
    
    try:
        # Proxy the request
        method = flask_request.method
        headers = {key: value for key, value in flask_request.headers if key.lower() != 'host'}
        
        if load_balancer.mock_mode:
            # Mock response in mock mode
            return jsonify({
                "message": f"[MOCK] Would route to {hostname}:5000/{path}",
                "server_id": server_id,
                "status": "successful"
            }), 200
        
        response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            data=flask_request.get_data(),
            params=flask_request.args,
            allow_redirects=False,
            timeout=5
        )
        
        # Check if endpoint exists (server returned 404)
        if response.status_code == 404:
            return jsonify({
                "message": f"<Error> '/{path}' endpoint does not exist in server replicas",
                "status": "failure"
            }), 400
        
        # Return proxied response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in response.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(response.content, response.status_code, headers)
        
    except requests.exceptions.Timeout:
        return jsonify({
            "message": f"<Error> Request to {hostname} timed out",
            "status": "failure"
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "message": f"<Error> Cannot connect to {hostname}",
            "status": "failure"
        }), 503
    except Exception as e:
        return jsonify({
            "message": f"<Error> {str(e)}",
            "status": "failure"
        }), 500


if __name__ == '__main__':
    try:
        # Ensure Docker network exists
        ensure_docker_network()
        
        # Seed replicas on startup
        seed_replicas()
        
        # Start health check monitoring
        load_balancer.start_health_checks()
        
        # Run load balancer on port 5000
        port = int(os.environ.get('LB_PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\nStopping load balancer...")
        load_balancer.stop_health_checks()
    except Exception as e:
        print(f"Error: {e}")
        load_balancer.stop_health_checks()
