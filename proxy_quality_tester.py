import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# URL to test proxies against (should be a real eBay item page that is always available)
TEST_URL = "https://www.ebay.com/itm/365712943558"  # You can change this to any stable eBay item

def get_local_ip():
    print("Retrieving local IP...")
    try:
        response = requests.get("http://ipinfo.io/ip", timeout=10)
        local_ip = response.text.strip()
        print(f"Local IP retrieved: {local_ip}")
        return local_ip
    except requests.RequestException as e:
        print(f"Failed to get local IP: {str(e)}")
        return None

def test_proxy_quality(proxy, local_ip, attempts=3):
    print(f"Starting test for proxy: {proxy}")
    ip, port = proxy.split(':')
    port = int(port)
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    successes = 0
    total_latency = 0.0
    proxied_ips = set()
    for i in range(attempts):
        print(f"Attempt {i+1}/{attempts} for {proxy}...")
        start_time = time.time()
        try:
            # Test by fetching a real eBay item page and expect HTTP 200
            response = requests.get(TEST_URL, proxies=proxies, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.ebay.com/'
            })
            if response.status_code == 200:
                latency = time.time() - start_time
                successes += 1
                total_latency += latency
                print(f"Success on attempt {i+1}: Latency {latency:.2f}s, Status 200")
            else:
                print(f"Failed on attempt {i+1}: Status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Failed on attempt {i+1}: {str(e)}")
    return {
        "ip": ip,
        "port": port,
        "success_rate": successes / attempts if attempts > 0 else 0,
        "avg_latency": total_latency / successes if successes > 0 else float('inf'),
        "anonymity": None,  # Not tested in this mode
        "quality_score": (successes / attempts) * (1 / (total_latency / successes + 1)) if successes > 0 else 0
    }

def write_json_atomic(results, filename):
    # Write to a temp file and rename for atomicity
    tmp_filename = filename + '.tmp'
    with open(tmp_filename, 'w') as f:
        json.dump(results, f, indent=4)
    import os
    os.replace(tmp_filename, filename)

if __name__ == "__main__":
    print("Starting proxy quality tester (multi-threaded)...")
    with open("proxies.txt", "r") as f:
        proxies = [line.strip() for line in f if line.strip() and ':' in line.strip()]

    local_ip = get_local_ip()
    if local_ip is None:
        print("Could not retrieve local IP. Exiting.")
        exit(1)

    results = []
    results_lock = threading.Lock()
    output_file = "proxies_quality.json"

    def process_and_write(proxy):
        result = test_proxy_quality(proxy, local_ip)
        if result["success_rate"] > 0:
            with results_lock:
                results.append(result)
                # Sort and write after each addition
                results.sort(key=lambda x: x["quality_score"], reverse=True)
                write_json_atomic(results, output_file)
        return result

    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_proxy = {executor.submit(process_and_write, proxy): proxy for proxy in proxies}
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    _ = future.result()
                except Exception as exc:
                    print(f"Proxy {proxy} generated an exception: {exc}")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Progress saved to proxies_quality.json.")
    print(f"Done. {len(results)} working proxies saved to {output_file}.") 