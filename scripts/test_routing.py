"""
Test script for request routing and health check features.

Tests the catch-all route handler, request proxying, and auto-respawn.
"""
import requests
import json
import time
import subprocess


BASE_URL = "http://localhost:5000"


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}\n")


def test_routing_home():
    """Test routing /home request to backend server."""
    print_section("Test 1: Route /home to Backend Server")
    
    try:
        response = requests.get(f"{BASE_URL}/home")
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Should get response from backend server with SERVER_ID
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "message" in data, "Missing 'message' field"
        assert "Hello from Server:" in data["message"], "Not a server response"
        
        print(f"\n✅ Successfully routed to backend server")
        print(f"   Server message: {data['message']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_routing_heartbeat():
    """Test routing /heartbeat request."""
    print_section("Test 2: Route /heartbeat to Backend Server")
    
    try:
        response = requests.get(f"{BASE_URL}/heartbeat")
        
        print(f"Status: {response.status_code}")
        print(f"Response body: '{response.text}'")
        
        # Heartbeat should return 200 with empty body
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"\n✅ Heartbeat routed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_nonexistent_endpoint():
    """Test requesting non-existent endpoint."""
    print_section("Test 3: Request Non-existent Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/nonexistent")
        
        print(f"Status: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Should return 400 with error message
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "does not exist" in data.get("message", ""), "Wrong error message"
            
            print(f"\n✅ Correctly rejected non-existent endpoint")
        else:
            print(f"Response text: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_load_distribution():
    """Test that requests are distributed across replicas."""
    print_section("Test 4: Load Distribution Across Replicas")
    
    try:
        server_ids = set()
        
        # Make multiple requests and collect server IDs
        for i in range(20):
            response = requests.get(f"{BASE_URL}/home")
            if response.status_code == 200:
                data = response.json()
                message = data.get("message", "")
                # Extract server ID from message like "Hello from Server: 1"
                if "Server:" in message:
                    server_id = message.split("Server:")[1].strip()
                    server_ids.add(server_id)
        
        print(f"Unique servers that handled requests: {sorted(server_ids)}")
        print(f"Number of unique servers: {len(server_ids)}")
        
        # Should hit multiple servers (at least 2 out of 3)
        assert len(server_ids) >= 2, "Requests not distributed across servers"
        
        print(f"\n✅ Requests distributed across {len(server_ids)} servers")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_health_check_status():
    """Check current replica status."""
    print_section("Test 5: Current Replica Status")
    
    try:
        response = requests.get(f"{BASE_URL}/rep")
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        print(f"\nCurrent replicas: {data['message']['N']}")
        print(f"Hostnames: {data['message']['replicas']}")
        
        print(f"\n✅ Replica status retrieved")
        
        return data['message']['N'], data['message']['replicas']
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


def test_auto_respawn_simulation():
    """
    Provide instructions for manual testing of auto-respawn.
    
    Note: This requires Docker and cannot be automated easily.
    """
    print_section("Test 6: Auto-Respawn (Manual Test)")
    
    print("To test auto-respawn functionality:")
    print()
    print("1. Note the current replicas:")
    initial_count, initial_replicas = test_health_check_status()
    
    if initial_count and initial_count > 0:
        target_replica = initial_replicas[0]
        print(f"\n2. Kill a container (in another terminal):")
        print(f"   docker kill {target_replica}")
        print()
        print(f"3. Wait 5-10 seconds for health check to detect failure")
        print()
        print(f"4. Check docker ps to see new container spawned:")
        print(f"   docker ps --filter network=net1")
        print()
        print(f"5. Verify replica count is maintained:")
        print(f"   curl {BASE_URL}/rep")
        print()
        print("Expected: New container appears with random name, N remains the same")
    
    print("\nℹ️  Auto-respawn test requires manual execution")


def wait_for_respawn(initial_replicas, timeout=15):
    """
    Wait for auto-respawn to occur after a container is killed.
    
    Args:
        initial_replicas: List of initial replica hostnames
        timeout: Max seconds to wait
        
    Returns:
        True if respawn detected, False otherwise
    """
    print(f"\n⏳ Waiting up to {timeout}s for auto-respawn...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/rep")
            if response.status_code == 200:
                data = response.json()
                current_replicas = data['message']['replicas']
                
                # Check if replicas changed
                if set(current_replicas) != set(initial_replicas):
                    print(f"✅ Respawn detected!")
                    print(f"   New replicas: {current_replicas}")
                    return True
        except:
            pass
        
        time.sleep(1)
    
    print(f"⏱️  Timeout waiting for respawn")
    return False


if __name__ == '__main__':
    try:
        print("\n" + "="*60)
        print("Load Balancer Routing & Health Check Tests")
        print("="*60)
        
        test_routing_home()
        time.sleep(0.5)
        
        test_routing_heartbeat()
        time.sleep(0.5)
        
        test_nonexistent_endpoint()
        time.sleep(0.5)
        
        test_load_distribution()
        time.sleep(0.5)
        
        test_health_check_status()
        time.sleep(0.5)
        
        test_auto_respawn_simulation()
        
        print("\n" + "="*60)
        print("✅ All Automated Tests Completed!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to load balancer")
        print("Make sure the load balancer is running:")
        print("  python load_balancer/app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
