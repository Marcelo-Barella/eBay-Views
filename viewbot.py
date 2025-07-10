import requests
import threading
import random
import json
import os
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent

# Load proxies from quality JSON file with fallback to txt file
def load_proxies():
    proxies = []
    proxy_weights = []
    
    # Try to load from quality JSON first
    if os.path.exists('proxies_quality.json'):
        try:
            with open('proxies_quality.json', 'r') as f:
                quality_data = json.load(f)
            
            if quality_data:
                for proxy_info in quality_data:
                    proxy_string = f"{proxy_info['ip']}:{proxy_info['port']}"
                    proxies.append(proxy_string)
                    # Use quality_score as weight, ensure minimum weight of 0.01
                    proxy_weights.append(max(proxy_info['quality_score'], 0.01))
                
                print(f"Loaded {len(proxies)} quality-tested proxies from proxies_quality.json")
                return proxies, proxy_weights
            else:
                print("proxies_quality.json is empty, falling back to proxies.txt")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error loading proxies_quality.json: {e}, falling back to proxies.txt")
    
    # Fallback to original txt file
    try:
        with open('proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        proxy_weights = [1.0] * len(proxies)  # Equal weights for txt file
        print(f"Loaded {len(proxies)} proxies from proxies.txt")
        return proxies, proxy_weights
    except FileNotFoundError:
        print("Neither proxies_quality.json nor proxies.txt found!")
        return [], []

proxies, proxy_weights = load_proxies()
ua = UserAgent()

def getRandomProxy():
    if not proxies:
        return None
    
    # Use weighted random selection based on quality scores
    if len(proxies) == 1:
        return proxies[0]
    
    return random.choices(proxies, weights=proxy_weights, k=1)[0]

def getRandomUA():
    return ua.random

def view_item(url):
    proxy = getRandomProxy()
    if not proxy:
        print("No proxies available!")
        return
    
    user_agent = getRandomUA()
    
    proxies_dict = {'http': f'http://{proxy}','https': f'http://{proxy}'}
    
    headers = {'User-Agent': user_agent}
    
    try:
        response = requests.get(url, proxies=proxies_dict, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"View successful - Proxy: {proxy}")
        else:
            print(f"View failed - Status Code: {response.status_code} - Proxy: {proxy}")
    except Exception as e:
        pass

def main():
    if not proxies:
        print("No proxies loaded. Please ensure proxies_quality.json or proxies.txt exists.")
        return
    
    url = input("URL: ")

    try:
        amount = int(input("Amount of Views: "))
    except ValueError:
        print("Failed to give valid number: defaulting to 500")
        amount = 500

    try:
        maxWorkers = int(input("Max Workers: "))
    except ValueError:
        print("Failed to give valid number: defaulting to 500")
        maxWorkers = 500
    
    with ThreadPoolExecutor(max_workers=maxWorkers) as executor:
        for _ in range(amount):
            executor.submit(view_item, url)

if __name__ == "__main__":
    main()
