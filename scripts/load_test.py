"""
Async load testing client using asyncio and aiohttp.

Provides utilities for sending concurrent requests to the load balancer.
"""
import asyncio
import aiohttp
import time
from typing import Dict, List, Tuple
from collections import Counter


class LoadTestClient:
    """
    Async HTTP client for load testing.
    
    Uses aiohttp for concurrent requests with connection pooling.
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize load test client.
        
        Args:
            base_url: Base URL of the load balancer
        """
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def send_request(self, path: str) -> Tuple[int, str, float]:
        """
        Send a single async HTTP request.
        
        Args:
            path: Request path (e.g., "/home")
            
        Returns:
            Tuple of (status_code, response_text, duration_ms)
        """
        url = f"{self.base_url}{path}"
        start_time = time.time()
        
        try:
            async with self.session.get(url) as response:
                text = await response.text()
                duration = (time.time() - start_time) * 1000  # Convert to ms
                return response.status, text, duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return 0, str(e), duration
    
    async def send_requests_batch(self, path: str, count: int) -> List[Tuple[int, str, float]]:
        """
        Send multiple concurrent requests.
        
        Args:
            path: Request path
            count: Number of requests to send
            
        Returns:
            List of (status_code, response_text, duration_ms) tuples
        """
        tasks = [self.send_request(path) for _ in range(count)]
        results = await asyncio.gather(*tasks)
        return results


def extract_server_id(response_text: str) -> str:
    """
    Extract server ID from response text.
    
    Args:
        response_text: JSON response string
        
    Returns:
        Server ID or "unknown"
    """
    try:
        # Parse response like {"message": "Hello from Server: 2", ...}
        if "Hello from Server:" in response_text:
            start = response_text.find("Hello from Server:") + len("Hello from Server:")
            # Extract the number after "Server: "
            server_id = ""
            for char in response_text[start:]:
                if char.isdigit():
                    server_id += char
                elif server_id:  # Stop after first number sequence
                    break
            return server_id if server_id else "unknown"
    except Exception:
        pass
    return "unknown"


def analyze_results(results: List[Tuple[int, str, float]]) -> Dict:
    """
    Analyze load test results.
    
    Args:
        results: List of (status_code, response_text, duration_ms) tuples
        
    Returns:
        Dictionary with analysis results
    """
    total_requests = len(results)
    successful = sum(1 for status, _, _ in results if status == 200)
    failed = total_requests - successful
    
    # Extract server IDs from successful requests
    server_ids = []
    for status, text, _ in results:
        if status == 200:
            server_id = extract_server_id(text)
            if server_id != "unknown":
                server_ids.append(server_id)
    
    # Count requests per server
    server_counts = Counter(server_ids)
    
    # Calculate latency statistics
    durations = [d for _, _, d in results]
    avg_latency = sum(durations) / len(durations) if durations else 0
    min_latency = min(durations) if durations else 0
    max_latency = max(durations) if durations else 0
    
    # Calculate percentiles
    sorted_durations = sorted(durations)
    p50_idx = int(len(sorted_durations) * 0.50)
    p95_idx = int(len(sorted_durations) * 0.95)
    p99_idx = int(len(sorted_durations) * 0.99)
    
    p50 = sorted_durations[p50_idx] if sorted_durations else 0
    p95 = sorted_durations[p95_idx] if sorted_durations else 0
    p99 = sorted_durations[p99_idx] if sorted_durations else 0
    
    return {
        "total_requests": total_requests,
        "successful": successful,
        "failed": failed,
        "server_counts": dict(server_counts),
        "latency_ms": {
            "avg": round(avg_latency, 2),
            "min": round(min_latency, 2),
            "max": round(max_latency, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        }
    }


def print_results(analysis: Dict, test_name: str = "Load Test"):
    """
    Print formatted analysis results.
    
    Args:
        analysis: Analysis dictionary from analyze_results()
        test_name: Name of the test
    """
    print(f"\n{'='*60}")
    print(f"{test_name} Results")
    print(f"{'='*60}")
    
    print(f"\nRequests:")
    print(f"  Total:      {analysis['total_requests']}")
    print(f"  Successful: {analysis['successful']}")
    print(f"  Failed:     {analysis['failed']}")
    
    print(f"\nServer Distribution:")
    server_counts = analysis['server_counts']
    for server_id in sorted(server_counts.keys()):
        count = server_counts[server_id]
        percentage = (count / analysis['successful']) * 100 if analysis['successful'] > 0 else 0
        bar = '█' * int(percentage / 2)
        print(f"  Server {server_id}: {count:5d} ({percentage:5.2f}%) {bar}")
    
    latency = analysis['latency_ms']
    print(f"\nLatency (ms):")
    print(f"  Average: {latency['avg']}")
    print(f"  Min:     {latency['min']}")
    print(f"  Max:     {latency['max']}")
    print(f"  P50:     {latency['p50']}")
    print(f"  P95:     {latency['p95']}")
    print(f"  P99:     {latency['p99']}")
    print()


async def run_load_test(base_url: str, path: str, count: int, test_name: str = "Load Test"):
    """
    Run a load test and print results.
    
    Args:
        base_url: Base URL of load balancer
        path: Request path
        count: Number of requests
        test_name: Name for this test
        
    Returns:
        Analysis dictionary
    """
    print(f"\n{'='*60}")
    print(f"Starting {test_name}")
    print(f"{'='*60}")
    print(f"Target:   {base_url}{path}")
    print(f"Requests: {count}")
    print("Running...")
    
    start_time = time.time()
    
    async with LoadTestClient(base_url) as client:
        results = await client.send_requests_batch(path, count)
    
    elapsed = time.time() - start_time
    
    print(f"Completed in {elapsed:.2f}s")
    print(f"Throughput: {count/elapsed:.2f} req/s")
    
    analysis = analyze_results(results)
    print_results(analysis, test_name)
    
    return analysis


if __name__ == '__main__':
    # Simple test
    async def main():
        analysis = await run_load_test(
            base_url="http://localhost:5000",
            path="/home",
            count=100,
            test_name="Quick Test"
        )
    
    asyncio.run(main())
