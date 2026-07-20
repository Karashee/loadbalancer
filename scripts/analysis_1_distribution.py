"""
Analysis 1: Load Distribution Test

Sends 10,000 async requests to /home with N=3 replicas.
Generates a bar chart showing request distribution across servers.

Output: results/a1_distribution.png
"""
import asyncio
import sys
import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.load_test import run_load_test


async def run_analysis_1(base_url: str = "http://localhost:5000"):
    """
    Run Analysis 1: Distribution test with N=3.
    
    Args:
        base_url: Load balancer URL
    """
    print("\n" + "="*60)
    print("ANALYSIS 1: LOAD DISTRIBUTION TEST")
    print("="*60)
    print()
    print("Configuration:")
    print("  Replicas (N): 3")
    print("  Requests:     10,000")
    print("  Endpoint:     /home")
    print()
    
    # Run load test
    analysis = await run_load_test(
        base_url=base_url,
        path="/home",
        count=10000,
        test_name="A-1: Distribution Test (N=3)"
    )
    
    # Extract server counts
    server_counts = analysis['server_counts']
    
    if not server_counts:
        print("❌ ERROR: No server data collected. Is the load balancer running?")
        return
    
    # Sort servers for consistent ordering
    servers = sorted(server_counts.keys())
    counts = [server_counts[s] for s in servers]
    
    # Calculate statistics
    total = sum(counts)
    avg_per_server = total / len(servers) if servers else 0
    percentages = [(c / total) * 100 if total > 0 else 0 for c in counts]
    
    print(f"\n{'='*60}")
    print("Distribution Analysis")
    print(f"{'='*60}")
    print(f"\nTotal requests routed: {total}")
    print(f"Number of servers: {len(servers)}")
    print(f"Average per server: {avg_per_server:.1f} ({100/len(servers):.1f}%)")
    print()
    
    for server, count, pct in zip(servers, counts, percentages):
        deviation = count - avg_per_server
        deviation_pct = (deviation / avg_per_server) * 100 if avg_per_server > 0 else 0
        print(f"Server {server}: {count:5d} ({pct:5.2f}%) [deviation: {deviation:+.0f} ({deviation_pct:+.1f}%)]")
    
    # Calculate standard deviation
    import math
    variance = sum((c - avg_per_server) ** 2 for c in counts) / len(counts)
    std_dev = math.sqrt(variance)
    cv = (std_dev / avg_per_server) * 100 if avg_per_server > 0 else 0
    
    print(f"\nStandard deviation: {std_dev:.2f}")
    print(f"Coefficient of variation: {cv:.2f}%")
    
    # Generate bar chart
    print(f"\n{'='*60}")
    print("Generating Bar Chart")
    print(f"{'='*60}")
    
    plt.figure(figsize=(10, 6))
    
    # Create bar chart
    bars = plt.bar(servers, counts, color='steelblue', edgecolor='black')
    
    # Add average line
    plt.axhline(y=avg_per_server, color='red', linestyle='--', 
                label=f'Average: {avg_per_server:.0f}')
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}\n({count/total*100:.1f}%)',
                ha='center', va='bottom', fontsize=10)
    
    # Formatting
    plt.xlabel('Server ID', fontsize=12, fontweight='bold')
    plt.ylabel('Request Count', fontsize=12, fontweight='bold')
    plt.title('A-1: Load Distribution Across Servers (N=3, 10K requests)', 
             fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # Save chart
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'a1_distribution.png')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Chart saved: {output_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    # Check if distribution is roughly even
    max_deviation = max(abs(c - avg_per_server) for c in counts)
    max_deviation_pct = (max_deviation / avg_per_server) * 100 if avg_per_server > 0 else 0
    
    if max_deviation_pct < 20:
        print("✅ Distribution is GOOD: Requests are roughly evenly distributed")
    elif max_deviation_pct < 40:
        print("⚠️  Distribution is FAIR: Some imbalance detected")
    else:
        print("❌ Distribution is POOR: Significant imbalance detected")
    
    print(f"\nMax deviation from average: {max_deviation:.0f} ({max_deviation_pct:.1f}%)")
    print(f"Coefficient of variation: {cv:.2f}%")
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_analysis_1())
        print("\n" + "="*60)
        print("✅ ANALYSIS 1 COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
