"""
Demo script to visualize consistent hash distribution.

Shows load distribution across servers with different configurations.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing.consistent_hash import ConsistentHashMap
from collections import Counter


def demo_distribution(num_servers: int, num_requests: int):
    """
    Demonstrate load distribution across servers.
    
    Args:
        num_servers: Number of servers to add
        num_requests: Number of requests to simulate
    """
    print(f"\n{'='*60}")
    print(f"Consistent Hash Distribution Demo")
    print(f"Servers: {num_servers}, Requests: {num_requests}")
    print(f"{'='*60}\n")
    
    # Initialize hash map and add servers
    hash_map = ConsistentHashMap()
    for server_id in range(1, num_servers + 1):
        hash_map.add_server(server_id)
    
    # Map requests and count distribution
    server_counts = Counter()
    for request_id in range(num_requests):
        server = hash_map.get_server(request_id)
        server_counts[server] += 1
    
    # Display results
    print("Load Distribution:")
    print(f"{'Server':<10} {'Requests':<12} {'Percentage':<12} {'Bar'}")
    print("-" * 60)
    
    for server_id in sorted(server_counts.keys()):
        count = server_counts[server_id]
        percentage = (count / num_requests) * 100
        bar_length = int(percentage / 2)  # Scale down for display
        bar = '█' * bar_length
        
        print(f"Server {server_id:<3} {count:<12} {percentage:>5.2f}%       {bar}")
    
    print()
    
    # Show virtual node distribution
    print("Virtual Node Slot Distribution:")
    for server_id in sorted(hash_map.server_slots.keys()):
        slots = sorted(hash_map.server_slots[server_id])
        print(f"Server {server_id}: {slots}")


if __name__ == '__main__':
    # Demo 1: 3 servers, 10,000 requests
    demo_distribution(3, 10000)
    
    # Demo 2: 5 servers, 10,000 requests
    demo_distribution(5, 10000)
    
    # Demo 3: 10 servers, 10,000 requests
    demo_distribution(10, 10000)
