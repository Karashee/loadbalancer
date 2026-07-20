"""
Analysis 4: Hash Function Comparison

Tests different hash functions (H for requests, Φ for virtual nodes)
and compares their impact on load distribution.

Re-runs A-1 and A-2 style tests with alternate hash functions.

Output: 
  - results/a4_hash_comparison_distribution.png
  - results/a4_hash_comparison_scalability.png
"""
import sys
import os
import asyncio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing.consistent_hash import ConsistentHashMap
from hashing.alternate_hash import ALTERNATE_HASHES
from collections import Counter


def test_hash_distribution(hash_name: str, request_hash_func, vnode_hash_func, 
                           num_servers: int = 3, num_requests: int = 10000):
    """
    Test distribution with specific hash functions.
    
    Args:
        hash_name: Name of hash function for labeling
        request_hash_func: Hash function for requests (H)
        vnode_hash_func: Hash function for virtual nodes (Φ)
        num_servers: Number of servers
        num_requests: Number of requests to simulate
        
    Returns:
        Dictionary with distribution statistics
    """
    # Create hash map with custom hash functions
    hash_map = ConsistentHashMap()
    
    # Temporarily replace hash functions
    original_hash_request = hash_map._hash_request
    original_hash_vnode = hash_map._hash_virtual_node
    
    def custom_hash_request(request_id):
        hash_value = request_hash_func(str(request_id))
        return hash_value % hash_map.RING_SIZE
    
    def custom_hash_vnode(server_id, virtual_index):
        combined = f"{server_id}:{virtual_index}"
        hash_value = vnode_hash_func(combined)
        return hash_value % hash_map.RING_SIZE
    
    hash_map._hash_request = custom_hash_request
    hash_map._hash_virtual_node = custom_hash_vnode
    
    # Add servers
    for server_id in range(1, num_servers + 1):
        hash_map.add_server(server_id)
    
    # Simulate requests
    server_counts = Counter()
    for request_id in range(num_requests):
        server_id = hash_map.get_server(request_id)
        if server_id is not None:
            server_counts[server_id] += 1
    
    # Calculate statistics
    counts = [server_counts[sid] for sid in range(1, num_servers + 1)]
    avg = sum(counts) / len(counts) if counts else 0
    
    variance = sum((c - avg) ** 2 for c in counts) / len(counts) if counts else 0
    std_dev = variance ** 0.5
    cv = (std_dev / avg * 100) if avg > 0 else 0
    
    max_dev = max(abs(c - avg) for c in counts) if counts else 0
    max_dev_pct = (max_dev / avg * 100) if avg > 0 else 0
    
    return {
        'hash_name': hash_name,
        'server_counts': dict(server_counts),
        'avg': avg,
        'std_dev': std_dev,
        'cv': cv,
        'max_dev': max_dev,
        'max_dev_pct': max_dev_pct,
    }


async def run_analysis_4():
    """
    Run Analysis 4: Hash function comparison.
    """
    print("\n" + "="*60)
    print("ANALYSIS 4: HASH FUNCTION COMPARISON")
    print("="*60)
    print()
    
    # Test configurations
    hash_functions_to_test = ['sha256', 'md5', 'fnv1a', 'djb2', 'simple']
    
    print("Testing hash functions:")
    for hf in hash_functions_to_test:
        print(f"  - {hf}")
    print()
    
    # Part 1: Distribution test (like A-1) with N=3
    print(f"\n{'='*60}")
    print("Part 1: Distribution Test (N=3, 10K requests)")
    print(f"{'='*60}\n")
    
    distribution_results = []
    
    for hash_name in hash_functions_to_test:
        print(f"Testing with {hash_name}...")
        hash_func = ALTERNATE_HASHES[hash_name]
        
        result = await asyncio.to_thread(
            test_hash_distribution,
            hash_name, hash_func, hash_func, 3, 10000
        )
        
        distribution_results.append(result)
        
        print(f"  CV: {result['cv']:.2f}%  Max Dev: {result['max_dev_pct']:.2f}%")
    
    # Part 2: Scalability test (like A-2) with varying N
    print(f"\n{'='*60}")
    print("Part 2: Scalability Test (N=2-6, 10K requests)")
    print(f"{'='*60}\n")
    
    scalability_results = {}
    n_values = [2, 3, 4, 5, 6]
    
    for hash_name in hash_functions_to_test:
        print(f"Testing with {hash_name}...")
        hash_func = ALTERNATE_HASHES[hash_name]
        scalability_results[hash_name] = []
        
        for n in n_values:
            result = await asyncio.to_thread(
                test_hash_distribution,
                hash_name, hash_func, hash_func, n, 10000
            )
            
            avg_load = result['avg']
            scalability_results[hash_name].append(avg_load)
        
        print(f"  Average loads: {[int(x) for x in scalability_results[hash_name]]}")
    
    # Generate comparison charts
    print(f"\n{'='*60}")
    print("Generating Comparison Charts")
    print(f"{'='*60}")
    
    # Chart 1: Distribution comparison (bar chart)
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(hash_functions_to_test))
    width = 0.25
    
    # Get server counts for each hash function
    server1_counts = [r['server_counts'].get(1, 0) for r in distribution_results]
    server2_counts = [r['server_counts'].get(2, 0) for r in distribution_results]
    server3_counts = [r['server_counts'].get(3, 0) for r in distribution_results]
    
    ax1.bar(x - width, server1_counts, width, label='Server 1', color='steelblue')
    ax1.bar(x, server2_counts, width, label='Server 2', color='coral')
    ax1.bar(x + width, server3_counts, width, label='Server 3', color='lightgreen')
    
    # Add average line
    avg_line = 10000 / 3
    ax1.axhline(y=avg_line, color='red', linestyle='--', label='Ideal Average')
    
    ax1.set_xlabel('Hash Function', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Request Count', fontsize=12, fontweight='bold')
    ax1.set_title('A-4: Distribution Comparison Across Hash Functions (N=3, 10K requests)', 
                 fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(hash_functions_to_test)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    output_path1 = os.path.join(output_dir, 'a4_hash_comparison_distribution.png')
    
    plt.savefig(output_path1, dpi=300, bbox_inches='tight')
    print(f"\n✅ Distribution chart saved: {output_path1}")
    
    # Chart 2: Scalability comparison (line chart)
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    
    colors = ['steelblue', 'coral', 'lightgreen', 'purple', 'orange']
    
    for idx, hash_name in enumerate(hash_functions_to_test):
        loads = scalability_results[hash_name]
        ax2.plot(n_values, loads, marker='o', linewidth=2, 
                markersize=8, color=colors[idx], label=hash_name)
    
    # Add ideal line
    ideal_loads = [10000 / n for n in n_values]
    ax2.plot(n_values, ideal_loads, '--', color='red', 
            label='Ideal (10000/N)', linewidth=2, alpha=0.7)
    
    ax2.set_xlabel('Number of Replicas (N)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Load per Server', fontsize=12, fontweight='bold')
    ax2.set_title('A-4: Scalability Comparison Across Hash Functions', 
                 fontsize=14, fontweight='bold')
    ax2.set_xticks(n_values)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_path2 = os.path.join(output_dir, 'a4_hash_comparison_scalability.png')
    
    plt.savefig(output_path2, dpi=300, bbox_inches='tight')
    print(f"✅ Scalability chart saved: {output_path2}")
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("Distribution Quality Summary (N=3)")
    print(f"{'='*60}\n")
    
    print(f"{'Hash Function':<15} {'CV (%)':<10} {'Max Dev (%)':<15} {'Quality'}")
    print("-" * 60)
    
    for result in distribution_results:
        quality = "Excellent" if result['cv'] < 10 else "Good" if result['cv'] < 20 else "Fair"
        print(f"{result['hash_name']:<15} {result['cv']:<10.2f} {result['max_dev_pct']:<15.2f} {quality}")
    
    print(f"\n{'='*60}")
    print("Observations")
    print(f"{'='*60}\n")
    
    # Find best and worst
    best = min(distribution_results, key=lambda x: x['cv'])
    worst = max(distribution_results, key=lambda x: x['cv'])
    
    print(f"✅ Best distribution:  {best['hash_name']} (CV: {best['cv']:.2f}%)")
    print(f"⚠️  Worst distribution: {worst['hash_name']} (CV: {worst['cv']:.2f}%)")
    
    # Check if SHA256 (original) is among the best
    sha256_result = [r for r in distribution_results if r['hash_name'] == 'sha256'][0]
    if sha256_result['cv'] <= best['cv'] * 1.1:  # Within 10% of best
        print(f"\n✅ SHA256 (original choice) performs well")
    else:
        print(f"\n💡 Alternative hash functions may provide better distribution")
    
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_analysis_4())
        print("\n" + "="*60)
        print("✅ ANALYSIS 4 COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
