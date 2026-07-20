"""
Analysis 3: Recovery Test

Tests load balancer recovery when a replica fails during active load.
Demonstrates auto-respawn and measures recovery timing.

Procedure:
1. Start load test with continuous requests
2. Kill a replica container mid-test
3. Measure detection time and recovery time
4. Show that requests continue with minimal disruption

Output: results/a3_recovery.png (timeline chart)
"""
import asyncio
import time
import subprocess
import requests
import sys
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.load_test import LoadTestClient


async def continuous_load_test(base_url: str, duration_seconds: int, results_list: list):
    """
    Send continuous requests and record results with timestamps.
    
    Args:
        base_url: Load balancer URL
        duration_seconds: How long to run
        results_list: Shared list to store (timestamp, success, server_id, latency)
    """
    async with LoadTestClient(base_url) as client:
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                status, text, latency = await client.send_request("/home")
                timestamp = time.time() - start_time
                success = (status == 200)
                
                # Extract server ID
                server_id = "unknown"
                if success and "Hello from Server:" in text:
                    try:
                        start_idx = text.find("Hello from Server:") + len("Hello from Server:")
                        for char in text[start_idx:]:
                            if char.isdigit():
                                server_id += char if server_id == "unknown" else char
                            elif server_id != "unknown":
                                server_id = server_id[7:]  # Remove "unknown" prefix
                                break
                    except:
                        pass
                
                results_list.append((timestamp, success, server_id, latency))
                request_count += 1
                
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)
                
            except Exception as e:
                timestamp = time.time() - start_time
                results_list.append((timestamp, False, "error", 0))


def kill_replica(replica_name: str) -> float:
    """
    Kill a replica container and record the time.
    
    Args:
        replica_name: Name of container to kill
        
    Returns:
        Timestamp when container was killed
    """
    print(f"\n🔪 Killing replica: {replica_name}")
    start = time.time()
    
    try:
        result = subprocess.run(
            ["docker", "kill", replica_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ Container killed: {replica_name}")
            return time.time() - start
        else:
            print(f"✗ Failed to kill container: {result.stderr}")
            return 0
    except Exception as e:
        print(f"✗ Error killing container: {e}")
        return 0


def check_for_new_replica(initial_replicas: set, base_url: str, timeout: int = 30) -> tuple:
    """
    Poll /rep endpoint to detect when a new replica appears.
    
    Args:
        initial_replicas: Set of original replica names
        base_url: Load balancer URL
        timeout: Max seconds to wait
        
    Returns:
        Tuple of (new_replica_name, detection_time) or (None, 0)
    """
    print("\n🔍 Monitoring for new replica...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/rep", timeout=2)
            if response.status_code == 200:
                data = response.json()
                current_replicas = set(data['message']['replicas'])
                
                # Check for new replicas
                new_replicas = current_replicas - initial_replicas
                if new_replicas:
                    new_replica = list(new_replicas)[0]
                    detection_time = time.time() - start_time
                    print(f"✓ New replica detected: {new_replica} (after {detection_time:.2f}s)")
                    return new_replica, detection_time
        except:
            pass
        
        time.sleep(0.5)
    
    print(f"✗ No new replica detected after {timeout}s")
    return None, 0


async def run_analysis_3(base_url: str = "http://localhost:5000"):
    """
    Run Analysis 3: Recovery test.
    
    Args:
        base_url: Load balancer URL
    """
    print("\n" + "="*60)
    print("ANALYSIS 3: RECOVERY TEST")
    print("="*60)
    print()
    print("Configuration:")
    print("  Duration: 30 seconds")
    print("  Failure injection: Kill replica at t=10s")
    print("  Monitoring: Continuous request stream")
    print()
    
    # Get initial replica list
    print("Getting initial replica list...")
    try:
        response = requests.get(f"{base_url}/rep")
        data = response.json()
        initial_replicas = set(data['message']['replicas'])
        print(f"Initial replicas: {initial_replicas}")
        
        if len(initial_replicas) < 2:
            print("❌ Need at least 2 replicas to test recovery")
            return
        
        # Choose a replica to kill (not a randomly generated one)
        target_replica = None
        for replica in initial_replicas:
            if replica.startswith("server-") and replica[7:].isdigit():
                target_replica = replica
                break
        
        if not target_replica:
            target_replica = list(initial_replicas)[0]
        
        print(f"Target replica for failure: {target_replica}")
        
    except Exception as e:
        print(f"❌ Error getting initial replicas: {e}")
        return
    
    # Shared results list
    results = []
    
    # Timeline events
    events = []
    
    test_duration = 30  # seconds
    kill_time = 10  # Kill replica at 10 seconds
    
    print(f"\n{'='*60}")
    print("Starting continuous load test...")
    print(f"{'='*60}\n")
    
    # Start continuous load test
    load_task = asyncio.create_task(
        continuous_load_test(base_url, test_duration, results)
    )
    
    # Wait until kill time
    await asyncio.sleep(kill_time)
    
    # Kill replica
    kill_start = time.time()
    await asyncio.to_thread(kill_replica, target_replica)
    events.append(("kill", kill_time, target_replica))
    
    # Monitor for recovery
    new_replica, detection_time = await asyncio.to_thread(
        check_for_new_replica, initial_replicas, base_url, 20
    )
    
    if new_replica:
        recovery_time = kill_time + detection_time
        events.append(("recovery", recovery_time, new_replica))
        print(f"\n✅ Recovery completed in {detection_time:.2f}s")
    else:
        print(f"\n⚠️  No recovery detected within timeout")
    
    # Wait for load test to finish
    await load_task
    
    print(f"\n✅ Load test completed. Total requests: {len(results)}")
    
    # Analyze results
    print(f"\n{'='*60}")
    print("Analyzing Results")
    print(f"{'='*60}\n")
    
    # Count successes over time
    window_size = 1.0  # 1 second windows
    windows = {}
    
    for timestamp, success, server_id, latency in results:
        window = int(timestamp / window_size)
        if window not in windows:
            windows[window] = {"total": 0, "success": 0, "latency": []}
        
        windows[window]["total"] += 1
        if success:
            windows[window]["success"] += 1
            windows[window]["latency"].append(latency)
    
    # Calculate success rate and avg latency per window
    times = []
    success_rates = []
    avg_latencies = []
    
    for window in sorted(windows.keys()):
        t = window * window_size
        total = windows[window]["total"]
        success = windows[window]["success"]
        latencies = windows[window]["latency"]
        
        success_rate = (success / total * 100) if total > 0 else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        times.append(t)
        success_rates.append(success_rate)
        avg_latencies.append(avg_latency)
    
    # Generate timeline chart
    print(f"\n{'='*60}")
    print("Generating Timeline Chart")
    print(f"{'='*60}")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Success Rate over time
    ax1.plot(times, success_rates, linewidth=2, color='steelblue', label='Success Rate')
    ax1.axvline(x=kill_time, color='red', linestyle='--', linewidth=2, label=f'Replica Killed ({target_replica})')
    
    if new_replica:
        ax1.axvline(x=recovery_time, color='green', linestyle='--', linewidth=2, label=f'Recovery ({new_replica})')
    
    ax1.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('A-3: Request Success Rate During Replica Failure', fontsize=14, fontweight='bold')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 105])
    
    # Plot 2: Average Latency over time
    ax2.plot(times, avg_latencies, linewidth=2, color='coral', label='Avg Latency')
    ax2.axvline(x=kill_time, color='red', linestyle='--', linewidth=2, label='Replica Killed')
    
    if new_replica:
        ax2.axvline(x=recovery_time, color='green', linestyle='--', linewidth=2, label='Recovery')
    
    ax2.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Latency (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Response Latency During Replica Failure', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save chart
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'a3_recovery.png')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Chart saved: {output_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("Recovery Summary")
    print(f"{'='*60}\n")
    
    total_requests = len(results)
    successful_requests = sum(1 for _, success, _, _ in results if success)
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total requests:     {total_requests}")
    print(f"Successful:         {successful_requests} ({success_rate:.2f}%)")
    print(f"Failed:             {total_requests - successful_requests}")
    print()
    print(f"Failure injected:   t={kill_time:.1f}s ({target_replica})")
    
    if new_replica:
        print(f"Recovery detected:  t={recovery_time:.1f}s ({new_replica})")
        print(f"Recovery time:      {detection_time:.2f}s")
    else:
        print(f"Recovery:           Not detected within monitoring period")
    
    # Calculate impact
    failure_window_start = kill_time
    failure_window_end = recovery_time if new_replica else kill_time + 15
    
    requests_during_failure = [r for r in results if failure_window_start <= r[0] <= failure_window_end]
    if requests_during_failure:
        failed_during = sum(1 for _, success, _, _ in requests_during_failure if not success)
        print(f"\nRequests during failure window: {len(requests_during_failure)}")
        print(f"Failed during window: {failed_during}")
    
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_analysis_3())
        print("\n" + "="*60)
        print("✅ ANALYSIS 3 COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
