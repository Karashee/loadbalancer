"""
Analysis 2: Scalability Test

Tests load balancer performance with varying replica counts (N=2 to N=6).
Sends 10,000 requests for each configuration.
Generates a line chart showing average load per server vs. replica count.

Output: results/a2_scalability.png
"""
import asyncio
import sys
import os
import time
import requests
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.load_test import run_load_test


async def configure_replicas(target_n: int, base_url: str = "http://localhost:5000"):
    """
    Configure the load balancer to have exactly N replicas.
    
    Args:
        target_n: Target number of replicas
        base_url: Load balancer URL
    """
    # Get current replica count
    response = requests.get(f"{base_url}/rep")
    data = response.json()
    current_n = data['message']['N']
    current_replicas = data['message']['replicas']
    
    print(f"Current replicas: {current_n}")
    print(f"Target replicas: {target_n}")
    
    if current_n == target_n:
        print("✓ Already at target replica count")
        return
    
    elif current_n < target_n:
        # Add replicas
        to_add = target_n - current_n
        print(f"Adding {to_add} replicas...")
        
        response = requests.post(
            f"{base_url}/add",
            json={"n": to_add, "hostnames": []},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✓ Added {to_add} replicas")
        else:
            print(f"✗ Failed to add replicas: {response.text}")
            raise Exception("Failed to add replicas")
    
    else:
        # Remove replicas
        to_remove = current_n - target_n
        print(f"Removing {to_remove} replicas...")
        
        response = requests.delete(
            f"{base_url}/rm",
            json={"n": to_remove, "hostnames": []},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✓ Removed {to_remove} replicas")
        else:
            print(f"✗ Failed to remove replicas: {response.text}")
            raise Exception("Failed to remove replicas")
    
    # Wait for changes to stabilize
    print("Waiting for replica changes to stabilize...")
    time.sleep(3)
    
    # Verify
    response = requests.get(f"{base_url}/rep")
    data = response.json()
    actual_n = data['message']['N']
    
    if actual_n == target_n:
        print(f"✓ Verified: N = {actual_n}")
    else:
        print(f"⚠️  Warning: Expected N={target_n}, got N={actual_n}")


async def run_analysis_2(base_url: str = "http://localhost:5000"):
    """
    Run Analysis 2: Scalability test with N=2 to N=6.
    
    Args:
        base_url: Load balancer URL
    """
    print("\n" + "="*60)
    print("ANALYSIS 2: SCALABILITY TEST")
    print("="*60)
    print()
    print("Configuration:")
    print("  Replica range: N=2 to N=6")
    print("  Requests per N: 10,000")
    print("  Endpoint: /home")
    print()
    
    n_values = [2, 3, 4, 5, 6]
    avg_loads = []  # Average requests per server for each N
    throughputs = []  # Requests per second for each N
    latencies = []  # Average latency for each N
    
    for n in n_values:
        print(f"\n{'='*60}")
        print(f"Testing with N = {n}")
        print(f"{'='*60}\n")
        
        try:
            # Configure replicas
            await asyncio.to_thread(configure_replicas, n, base_url)
            
            # Run load test
            analysis = await run_load_test(
                base_url=base_url,
                path="/home",
                count=10000,
                test_name=f"A-2: Scalability Test (N={n})"
            )
            
            # Calculate average load per server
            server_counts = analysis['server_counts']
            total_requests = analysis['successful']
            
            if server_counts:
                avg_load = total_requests / len(server_counts)
                avg_loads.append(avg_load)
            else:
                print(f"⚠️  Warning: No server data for N={n}")
                avg_loads.append(0)
            
            # Store throughput and latency
            # Note: These would come from timing data in actual implementation
            # For now, using placeholder values from analysis
            throughputs.append(total_requests / 10)  # Placeholder
            latencies.append(analysis['latency_ms']['avg'])
            
            print(f"\nAverage load per server: {avg_loads[-1]:.1f} requests")
            
        except Exception as e:
            print(f"❌ Error testing N={n}: {e}")
            avg_loads.append(0)
            throughputs.append(0)
            latencies.append(0)
    
    # Generate line chart
    print(f"\n{'='*60}")
    print("Generating Line Chart")
    print(f"{'='*60}")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    
    # Plot 1: Average load per server
    ax1.plot(n_values, avg_loads, marker='o', linewidth=2, 
            markersize=8, color='steelblue', label='Avg Load per Server')
    
    # Add value labels
    for n, load in zip(n_values, avg_loads):
        ax1.text(n, load, f'{load:.0f}', ha='center', va='bottom', fontsize=10)
    
    # Add ideal line (total requests / N)
    total_requests = 10000
    ideal_loads = [total_requests / n for n in n_values]
    ax1.plot(n_values, ideal_loads, '--', color='red', 
            label='Ideal (10000/N)', alpha=0.7)
    
    ax1.set_xlabel('Number of Replicas (N)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Requests per Server', fontsize=12, fontweight='bold')
    ax1.set_title('A-2: Average Load per Server vs. Replica Count', 
                 fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(n_values)
    
    # Plot 2: Average latency
    ax2.plot(n_values, latencies, marker='s', linewidth=2, 
            markersize=8, color='coral', label='Avg Latency')
    
    # Add value labels
    for n, lat in zip(n_values, latencies):
        ax2.text(n, lat, f'{lat:.1f}ms', ha='center', va='bottom', fontsize=10)
    
    ax2.set_xlabel('Number of Replicas (N)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Latency (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Response Latency vs. Replica Count', 
                 fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(n_values)
    
    plt.tight_layout()
    
    # Save chart
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'a2_scalability.png')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Chart saved: {output_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}\n")
    
    print("Replica Count | Avg Load/Server | Avg Latency")
    print("-" * 60)
    for n, load, lat in zip(n_values, avg_loads, latencies):
        print(f"N = {n}         | {load:15.1f} | {lat:11.2f} ms")
    
    print(f"\n{'='*60}")
    print("Observations")
    print(f"{'='*60}\n")
    
    # Check if load decreases with more replicas (expected behavior)
    if avg_loads[0] > avg_loads[-1]:
        print("✅ Average load per server DECREASES as N increases (expected)")
    else:
        print("⚠️  Average load per server does NOT decrease as expected")
    
    # Check if latency behaves reasonably
    if max(latencies) < 1000:  # < 1 second
        print("✅ Latencies are reasonable (< 1s)")
    else:
        print("⚠️  Some latencies are high (> 1s)")
    
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_analysis_2())
        print("\n" + "="*60)
        print("✅ ANALYSIS 2 COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
