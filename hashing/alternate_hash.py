"""
Alternate hash function implementations for comparison.

Provides different hash functions to test impact on distribution quality.
"""
import hashlib


def hash_md5(value: str) -> int:
    """
    MD5-based hash function.
    
    Args:
        value: String to hash
        
    Returns:
        Integer hash value
    """
    hash_obj = hashlib.md5(value.encode())
    return int(hash_obj.hexdigest(), 16)


def hash_simple_multiplicative(value: str) -> int:
    """
    Simple multiplicative hash function.
    
    Uses prime multiplier for better distribution.
    
    Args:
        value: String to hash
        
    Returns:
        Integer hash value
    """
    hash_value = 0
    prime = 31
    
    for char in value:
        hash_value = hash_value * prime + ord(char)
    
    return abs(hash_value)


def hash_fnv1a(value: str) -> int:
    """
    FNV-1a hash function.
    
    Fast, non-cryptographic hash with good distribution.
    
    Args:
        value: String to hash
        
    Returns:
        Integer hash value
    """
    fnv_prime = 0x01000193
    fnv_offset = 0x811c9dc5
    
    hash_value = fnv_offset
    for byte in value.encode():
        hash_value ^= byte
        hash_value = (hash_value * fnv_prime) & 0xffffffff
    
    return hash_value


def hash_djb2(value: str) -> int:
    """
    DJB2 hash function by Dan Bernstein.
    
    Simple but effective hash function.
    
    Args:
        value: String to hash
        
    Returns:
        Integer hash value
    """
    hash_value = 5381
    
    for char in value:
        hash_value = ((hash_value << 5) + hash_value) + ord(char)
    
    return abs(hash_value)


# Alternate hash function mappings for testing
ALTERNATE_HASHES = {
    'sha256': lambda v: int(hashlib.sha256(v.encode()).hexdigest(), 16),  # Original
    'md5': hash_md5,
    'fnv1a': hash_fnv1a,
    'djb2': hash_djb2,
    'simple': hash_simple_multiplicative,
}


def get_hash_function(name: str):
    """
    Get hash function by name.
    
    Args:
        name: Hash function name ('sha256', 'md5', 'fnv1a', 'djb2', 'simple')
        
    Returns:
        Hash function
        
    Raises:
        ValueError: If hash function not found
    """
    if name not in ALTERNATE_HASHES:
        raise ValueError(f"Unknown hash function: {name}. Available: {list(ALTERNATE_HASHES.keys())}")
    
    return ALTERNATE_HASHES[name]
