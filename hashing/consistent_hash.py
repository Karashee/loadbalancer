"""
Consistent Hash Map implementation with virtual nodes and quadratic probing.

Uses a fixed-size ring of 512 slots with K=9 virtual nodes per server.
Collision resolution is handled via quadratic probing.
"""
from typing import Optional, Dict, Set
import hashlib


class ConsistentHashMap:
    """
    Consistent hash map with virtual nodes for load balancing.
    
    Attributes:
        RING_SIZE: Fixed ring size of 512 slots
        VIRTUAL_NODES: Number of virtual nodes per server (K=9)
    """
    
    RING_SIZE = 512
    VIRTUAL_NODES = 9
    
    def __init__(self):
        """Initialize empty hash ring."""
        # Array-backed ring: None = empty slot, server_id = occupied
        self.ring: list[Optional[int]] = [None] * self.RING_SIZE
        
        # Track which slots belong to which server for efficient removal
        self.server_slots: Dict[int, Set[int]] = {}
    
    def _hash_request(self, request_id: int) -> int:
        """
        Hash function H(Rid) for mapping requests to slots.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Slot index in range [0, 511]
        """
        # Use SHA-256 for uniform distribution
        hash_obj = hashlib.sha256(str(request_id).encode())
        hash_value = int(hash_obj.hexdigest(), 16)
        return hash_value % self.RING_SIZE
    
    def _hash_virtual_node(self, server_id: int, virtual_index: int) -> int:
        """
        Virtual node hash function Φ(i,j) for server placement.
        
        Args:
            server_id: Server identifier (i)
            virtual_index: Virtual node index (j) in range [0, K-1]
            
        Returns:
            Initial slot index in range [0, 511]
        """
        # Combine server_id and virtual_index for unique hash
        combined = f"{server_id}:{virtual_index}"
        hash_obj = hashlib.sha256(combined.encode())
        hash_value = int(hash_obj.hexdigest(), 16)
        return hash_value % self.RING_SIZE
    
    def _quadratic_probe(self, initial_slot: int, is_insert: bool = True) -> int:
        """
        Quadratic probing for collision resolution.
        
        Args:
            initial_slot: Starting slot index
            is_insert: If True, find empty slot; if False, find occupied slot
            
        Returns:
            Final slot index after probing
            
        Raises:
            RuntimeError: If ring is full (for insert) or empty (for lookup)
        """
        for i in range(self.RING_SIZE):
            # Quadratic probing: slot = (initial + i^2) % RING_SIZE
            probe_slot = (initial_slot + i * i) % self.RING_SIZE
            
            if is_insert:
                # Looking for empty slot
                if self.ring[probe_slot] is None:
                    return probe_slot
            else:
                # Looking for occupied slot (clockwise nearest)
                if self.ring[probe_slot] is not None:
                    return probe_slot
        
        if is_insert:
            raise RuntimeError("Hash ring is full")
        else:
            raise RuntimeError("Hash ring is empty")
    
    def add_server(self, server_id: int) -> None:
        """
        Add a server to the hash ring with K virtual nodes.
        
        Args:
            server_id: Unique server identifier
            
        Raises:
            ValueError: If server already exists
        """
        if server_id in self.server_slots:
            raise ValueError(f"Server {server_id} already exists")
        
        self.server_slots[server_id] = set()
        
        # Place K virtual nodes on the ring
        for j in range(self.VIRTUAL_NODES):
            initial_slot = self._hash_virtual_node(server_id, j)
            final_slot = self._quadratic_probe(initial_slot, is_insert=True)
            
            self.ring[final_slot] = server_id
            self.server_slots[server_id].add(final_slot)
    
    def remove_server(self, server_id: int) -> None:
        """
        Remove a server and all its virtual nodes from the ring.
        
        Args:
            server_id: Server identifier to remove
            
        Raises:
            ValueError: If server does not exist
        """
        if server_id not in self.server_slots:
            raise ValueError(f"Server {server_id} does not exist")
        
        # Remove all virtual nodes for this server
        for slot in self.server_slots[server_id]:
            self.ring[slot] = None
        
        del self.server_slots[server_id]
    
    def get_server(self, request_id: int) -> Optional[int]:
        """
        Map a request to a server using consistent hashing.
        
        Finds the clockwise nearest occupied slot from the request's hash.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Server ID that should handle the request, or None if ring is empty
        """
        if not self.server_slots:
            return None
        
        initial_slot = self._hash_request(request_id)
        
        # Find clockwise nearest occupied slot
        # Search from initial_slot to end of ring
        for offset in range(self.RING_SIZE):
            check_slot = (initial_slot + offset) % self.RING_SIZE
            if self.ring[check_slot] is not None:
                return self.ring[check_slot]
        
        # Should never reach here if ring is not empty
        return None
    
    def get_load_distribution(self) -> Dict[int, int]:
        """
        Get the number of slots occupied by each server.
        
        Returns:
            Dictionary mapping server_id to slot count
        """
        return {server_id: len(slots) 
                for server_id, slots in self.server_slots.items()}
