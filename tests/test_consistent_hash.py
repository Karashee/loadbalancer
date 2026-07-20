"""
Unit tests for consistent hash map implementation.

Tests load distribution, quadratic probing, and add/remove operations.
"""
import unittest
from collections import Counter
from hashing.consistent_hash import ConsistentHashMap


class TestConsistentHashMap(unittest.TestCase):
    """Test cases for ConsistentHashMap."""
    
    def setUp(self):
        """Initialize hash map before each test."""
        self.hash_map = ConsistentHashMap()
    
    def test_add_single_server(self):
        """Test adding a single server creates K virtual nodes."""
        self.hash_map.add_server(1)
        
        # Should have exactly K=9 virtual nodes
        self.assertEqual(len(self.hash_map.server_slots[1]), 
                        ConsistentHashMap.VIRTUAL_NODES)
        
        # All slots should contain server 1
        occupied_count = sum(1 for slot in self.hash_map.ring if slot == 1)
        self.assertEqual(occupied_count, ConsistentHashMap.VIRTUAL_NODES)
    
    def test_add_duplicate_server_raises_error(self):
        """Test that adding the same server twice raises ValueError."""
        self.hash_map.add_server(1)
        
        with self.assertRaises(ValueError):
            self.hash_map.add_server(1)
    
    def test_remove_server(self):
        """Test removing a server clears all its virtual nodes."""
        self.hash_map.add_server(1)
        self.hash_map.add_server(2)
        
        # Remove server 1
        self.hash_map.remove_server(1)
        
        # Server 1 should be gone
        self.assertNotIn(1, self.hash_map.server_slots)
        
        # No slots should contain server 1
        occupied_count = sum(1 for slot in self.hash_map.ring if slot == 1)
        self.assertEqual(occupied_count, 0)
        
        # Server 2 should still exist
        self.assertIn(2, self.hash_map.server_slots)
    
    def test_remove_nonexistent_server_raises_error(self):
        """Test removing a non-existent server raises ValueError."""
        with self.assertRaises(ValueError):
            self.hash_map.remove_server(999)
    
    def test_get_server_empty_ring(self):
        """Test that get_server returns None when ring is empty."""
        result = self.hash_map.get_server(12345)
        self.assertIsNone(result)
    
    def test_get_server_single_server(self):
        """Test that all requests map to the only server."""
        self.hash_map.add_server(1)
        
        # Test multiple requests all map to server 1
        for request_id in range(100):
            server = self.hash_map.get_server(request_id)
            self.assertEqual(server, 1)
    
    def test_quadratic_probing_collision_resolution(self):
        """Test that quadratic probing correctly resolves collisions."""
        # Add multiple servers - they should all find slots via probing
        for server_id in range(1, 11):
            self.hash_map.add_server(server_id)
        
        # Verify total virtual nodes placed
        total_slots = sum(len(slots) for slots in self.hash_map.server_slots.values())
        expected_slots = 10 * ConsistentHashMap.VIRTUAL_NODES
        self.assertEqual(total_slots, expected_slots)
        
        # Verify no collisions (each slot has at most one server)
        occupied_slots = [slot for slot in self.hash_map.ring if slot is not None]
        self.assertEqual(len(occupied_slots), expected_slots)
    
    def test_load_distribution_three_servers(self):
        """Test load distribution across 3 servers with ~10,000 requests."""
        # Add 3 servers
        self.hash_map.add_server(1)
        self.hash_map.add_server(2)
        self.hash_map.add_server(3)
        
        # Map 10,000 requests and count distribution
        request_count = 10000
        server_counts = Counter()
        
        for request_id in range(request_count):
            server = self.hash_map.get_server(request_id)
            server_counts[server] += 1
        
        # Print distribution for manual inspection
        print("\n--- Load Distribution Test (3 servers, 10,000 requests) ---")
        for server_id in sorted(server_counts.keys()):
            count = server_counts[server_id]
            percentage = (count / request_count) * 100
            print(f"Server {server_id}: {count:5d} requests ({percentage:5.2f}%)")
        
        # Each server should handle roughly 33.3% of requests
        # With only 9 virtual nodes and 512 slots, allow wider deviation
        # Acceptable range: 20% to 50% per server
        expected_per_server = request_count / 3
        min_acceptable = request_count * 0.20  # 20%
        max_acceptable = request_count * 0.50  # 50%
        
        for server_id in [1, 2, 3]:
            count = server_counts[server_id]
            percentage = (count / request_count) * 100
            self.assertGreater(count, min_acceptable,
                             f"Server {server_id} severely underloaded: {percentage:.1f}%")
            self.assertLess(count, max_acceptable,
                          f"Server {server_id} severely overloaded: {percentage:.1f}%")
    
    def test_add_remove_remaps_keys(self):
        """Test that adding/removing servers causes expected key remapping."""
        # Start with 2 servers
        self.hash_map.add_server(1)
        self.hash_map.add_server(2)
        
        # Map some requests
        test_requests = list(range(1000))
        initial_mapping = {rid: self.hash_map.get_server(rid) 
                          for rid in test_requests}
        
        # Add a third server
        self.hash_map.add_server(3)
        
        new_mapping = {rid: self.hash_map.get_server(rid) 
                      for rid in test_requests}
        
        # Some keys should have remapped to server 3
        remapped_count = sum(1 for rid in test_requests 
                           if initial_mapping[rid] != new_mapping[rid])
        
        print(f"\n--- Key Remapping Test (Add Server) ---")
        print(f"Remapped keys: {remapped_count}/{len(test_requests)} "
              f"({remapped_count/len(test_requests)*100:.1f}%)")
        
        # At least some keys should remap (roughly 1/3)
        self.assertGreater(remapped_count, 100, 
                          "Too few keys remapped when adding server")
        
        # Not all keys should remap (monotonicity property)
        self.assertLess(remapped_count, 900,
                       "Too many keys remapped when adding server")
        
        # Now remove server 3
        mapping_before_remove = new_mapping.copy()
        self.hash_map.remove_server(3)
        
        mapping_after_remove = {rid: self.hash_map.get_server(rid) 
                               for rid in test_requests}
        
        # Keys that were on server 3 should now map to servers 1 or 2
        keys_on_server_3 = [rid for rid in test_requests 
                           if mapping_before_remove[rid] == 3]
        
        print(f"\n--- Key Remapping Test (Remove Server) ---")
        print(f"Keys previously on server 3: {len(keys_on_server_3)}")
        
        # Verify those keys now map to other servers
        for rid in keys_on_server_3:
            self.assertIn(mapping_after_remove[rid], [1, 2],
                        f"Request {rid} not remapped correctly after removal")
    
    def test_virtual_node_slot_distribution(self):
        """Test that virtual nodes are distributed across the ring."""
        self.hash_map.add_server(1)
        
        # Get all slot positions for server 1
        slots = sorted(self.hash_map.server_slots[1])
        
        print(f"\n--- Virtual Node Distribution (Server 1) ---")
        print(f"Slot positions: {slots}")
        
        # Virtual nodes should not all be clustered together
        # Check that there's reasonable spacing
        min_slot = min(slots)
        max_slot = max(slots)
        span = max_slot - min_slot
        
        # Span should be at least 20% of ring size
        min_expected_span = ConsistentHashMap.RING_SIZE * 0.2
        self.assertGreater(span, min_expected_span,
                          "Virtual nodes too clustered")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
