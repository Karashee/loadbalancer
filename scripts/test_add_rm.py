"""
Test script for /add and /rm endpoints.

Verifies container spawning, removal, and error handling.
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


def check_docker_ps():
    """Display running containers on net1."""
    print("\n--- Docker Containers ---")
    result = subprocess.run(
        ["docker", "ps", "--filter", "network=net1", "--format", 
         "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
        capture_output=True,
        text=True
    )
    print(result.stdout)


def test_initial_state():
    """Test initial /rep endpoint."""
    print_section("Test 1: Initial State")
    
    response = requests.get(f"{BASE_URL}/rep")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert data['message']['N'] == 3, "Should have 3 initial replicas"
    print("\n✅ Initial state verified")


def test_add_two_servers():
    """Test adding 2 servers with explicit hostnames."""
    print_section("Test 2: Add 2 Servers with Hostnames")
    
    payload = {
        "n": 2,
        "hostnames": ["test-server-1", "test-server-2"]
    }
    
    print(f"Request: POST /add")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/add", json=payload)
    data = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        assert data['message']['N'] == 5, "Should have 5 replicas now"
        assert 'test-server-1' in data['message']['replicas']
        assert 'test-server-2' in data['message']['replicas']
        print("\n✅ Servers added successfully")
        
        # Check Docker
        check_docker_ps()
    else:
        print(f"\n❌ Failed to add servers: {data.get('message')}")


def test_add_auto_hostname():
    """Test adding servers with auto-generated hostnames."""
    print_section("Test 3: Add 1 Server with Auto Hostname")
    
    payload = {
        "n": 1,
        "hostnames": []
    }
    
    print(f"Request: POST /add")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/add", json=payload)
    data = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        assert data['message']['N'] == 6, "Should have 6 replicas now"
        print("\n✅ Server with auto hostname added")
        check_docker_ps()
    else:
        print(f"\n❌ Failed: {data.get('message')}")


def test_add_bad_payload():
    """Test adding with invalid payload (more hostnames than n)."""
    print_section("Test 4: Add with Bad Payload (too many hostnames)")
    
    payload = {
        "n": 1,
        "hostnames": ["host-a", "host-b", "host-c"]
    }
    
    print(f"Request: POST /add")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/add", json=payload)
    data = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert response.status_code == 400, "Should return 400 error"
    assert "more than newly added instances" in data['message']
    print("\n✅ Correctly rejected bad payload")


def test_remove_one():
    """Test removing 1 server by hostname."""
    print_section("Test 5: Remove 1 Server (test-server-1)")
    
    payload = {
        "n": 1,
        "hostnames": ["test-server-1"]
    }
    
    print(f"Request: DELETE /rm")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.delete(f"{BASE_URL}/rm", json=payload)
    data = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        assert 'test-server-1' not in data['message']['replicas']
        print("\n✅ Server removed successfully")
        check_docker_ps()
    else:
        print(f"\n❌ Failed: {data.get('message')}")


def test_remove_bad_payload():
    """Test removing with invalid payload (more hostnames than n)."""
    print_section("Test 6: Remove with Bad Payload (too many hostnames)")
    
    payload = {
        "n": 1,
        "hostnames": ["test-server-2", "server-1", "server-2"]
    }
    
    print(f"Request: DELETE /rm")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.delete(f"{BASE_URL}/rm", json=payload)
    data = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert response.status_code == 400, "Should return 400 error"
    assert "more than removable instances" in data['message']
    print("\n✅ Correctly rejected bad payload")


def test_final_state():
    """Check final state."""
    print_section("Test 7: Final State")
    
    response = requests.get(f"{BASE_URL}/rep")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    print(f"\nFinal replica count: {data['message']['N']}")
    
    check_docker_ps()


if __name__ == '__main__':
    try:
        test_initial_state()
        time.sleep(1)
        
        test_add_two_servers()
        time.sleep(2)
        
        test_add_auto_hostname()
        time.sleep(2)
        
        test_add_bad_payload()
        time.sleep(1)
        
        test_remove_one()
        time.sleep(2)
        
        test_remove_bad_payload()
        time.sleep(1)
        
        test_final_state()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to load balancer")
        print("Make sure the load balancer is running:")
        print("  python load_balancer/app.py")
    except AssertionError as e:
        print(f"\n❌ Test assertion failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
