"""
Simple test script for load balancer endpoints.

Tests the /rep endpoint to verify replica information.
"""
import requests
import json


def test_rep_endpoint(base_url: str = "http://localhost:5000"):
    """
    Test the /rep endpoint.
    
    Args:
        base_url: Base URL of the load balancer
    """
    print(f"\n{'='*60}")
    print("Testing Load Balancer /rep Endpoint")
    print(f"{'='*60}\n")
    
    try:
        # Test /rep endpoint
        response = requests.get(f"{base_url}/rep")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}\n")
        
        if response.status_code == 200:
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Verify structure
            print("\n--- Verification ---")
            assert "message" in data, "Missing 'message' field"
            assert "status" in data, "Missing 'status' field"
            assert data["status"] == "successful", "Status not successful"
            
            message = data["message"]
            assert "N" in message, "Missing 'N' field in message"
            assert "replicas" in message, "Missing 'replicas' field in message"
            
            print(f"✓ Replica count (N): {message['N']}")
            print(f"✓ Replicas: {message['replicas']}")
            
            # Verify 3 seeded replicas
            assert message['N'] == 3, f"Expected 3 replicas, got {message['N']}"
            assert len(message['replicas']) == 3, "Replica list length mismatch"
            
            print("\n✅ All checks passed!")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to load balancer")
        print("Make sure the load balancer is running:")
        print("  python load_balancer/app.py")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    test_rep_endpoint()
