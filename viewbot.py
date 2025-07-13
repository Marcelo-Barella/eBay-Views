import requests
import threading
import random
import json
import os
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
import logging
from datetime import datetime
import socket

# Set up verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load proxies from quality JSON file with fallback to txt file
def load_proxies():
    proxies = []
    proxy_weights = []
    logging.debug('Attempting to load proxies from proxies_quality.json or proxies.txt')
    
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
                
                logging.info(f"Loaded {len(proxies)} quality-tested proxies from proxies_quality.json")
                return proxies, proxy_weights
            else:
                logging.warning("proxies_quality.json is empty, falling back to proxies.txt")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            logging.error(f"Error loading proxies_quality.json: {e}, falling back to proxies.txt")
    
    # Fallback to original txt file
    try:
        with open('proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        proxy_weights = [1.0] * len(proxies)  # Equal weights for txt file
        logging.info(f"Loaded {len(proxies)} proxies from proxies.txt")
        return proxies, proxy_weights
    except FileNotFoundError:
        logging.critical("Neither proxies_quality.json nor proxies.txt found!")
        return [], []

proxies, proxy_weights = load_proxies()
ua = UserAgent()

# Validate if a proxy supports HTTPS CONNECT to a known site (e.g., www.google.com:443)
def validate_proxy(proxy, timeout=5):
    try:
        host, port = proxy.split(":")
        port = int(port)
        with socket.create_connection((host, port), timeout=timeout) as sock:
            connect_str = f"CONNECT www.google.com:443 HTTP/1.1\r\nHost: www.google.com:443\r\n\r\n"
            sock.sendall(connect_str.encode())
            response = sock.recv(4096)
            if b"200" in response:
                return True
    except Exception as e:
        logging.debug(f"Proxy validation failed for {proxy}: {e}")
    return False

# Remove dead proxies from the current run (in-memory only)
def remove_dead_proxy(proxy):
    try:
        idx = proxies.index(proxy)
        proxies.pop(idx)
        proxy_weights.pop(idx)
        logging.info(f"Removed dead proxy from current run: {proxy}")
    except ValueError:
        logging.debug(f"Proxy {proxy} not found in list for removal.")

def getRandomProxy():
    if not proxies:
        logging.error('No proxies available for selection!')
        return None
    
    # Use weighted random selection based on quality scores
    if len(proxies) == 1:
        logging.debug(f'Only one proxy available: {proxies[0]}')
        return proxies[0]
    
    proxy = random.choices(proxies, weights=proxy_weights, k=1)[0]
    logging.debug(f'Selected proxy: {proxy}')
    return proxy

def getRandomUA():
    user_agent = ua.random
    logging.debug(f'Selected User-Agent: {user_agent}')
    return user_agent

# Ensure pages directory exists
def ensure_pages_dir():
    pages_dir = 'pages'
    if not os.path.exists(pages_dir):
        try:
            os.makedirs(pages_dir)
            logging.info(f'Created directory: {pages_dir}')
        except Exception as e:
            logging.error(f'Failed to create pages directory: {e}', exc_info=True)
    return pages_dir

# Save HTML content to file
def save_html(content, status_code):
    pages_dir = ensure_pages_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f'view_{timestamp}_status{status_code}.html'
    file_path = os.path.join(pages_dir, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f'Saved HTML to {file_path}')
    except Exception as e:
        logging.error(f'Failed to save HTML to {file_path}: {e}', exc_info=True)

def view_item(url, max_proxy_attempts=5):
    attempts = 0
    while attempts < max_proxy_attempts:
        proxy = getRandomProxy()
        if not proxy:
            logging.error('No proxies available!')
            return
        # Validate proxy before use
        if not validate_proxy(proxy):
            logging.warning(f"Proxy {proxy} failed validation. Removing from current run.")
            remove_dead_proxy(proxy)
            attempts += 1
            continue
        user_agent = getRandomUA()
        proxies_dict = {'http': f'http://{proxy}','https': f'http://{proxy}'}
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-full-version': '"132.0.6834.160"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent,
            'Referer': 'https://www.ebay.com/',
        }
        try:
            logging.debug(f"Attempting to view {url} with proxy {proxy} and User-Agent: {user_agent}")
            response = requests.get(url, proxies=proxies_dict, headers=headers, timeout=10)
            logging.debug(f"Response status code: {response.status_code}")
            save_html(response.text, response.status_code)
            if response.status_code == 200:
                logging.info(f"View successful - Proxy: {proxy}")
                return
            else:
                logging.warning(f"View failed - Status Code: {response.status_code} - Proxy: {proxy}")
                # Remove proxy if status code indicates proxy is not working (e.g., 502, 400, 404)
                if response.status_code in (400, 404, 502, 407):
                    remove_dead_proxy(proxy)
                attempts += 1
        except requests.exceptions.ProxyError as e:
            logging.error(f"ProxyError during view attempt: {e}")
            remove_dead_proxy(proxy)
            attempts += 1
        except requests.exceptions.SSLError as e:
            logging.error(f"SSLError during view attempt: {e}")
            remove_dead_proxy(proxy)
            attempts += 1
        except requests.exceptions.ConnectTimeout as e:
            logging.error(f"ConnectTimeout during view attempt: {e}")
            remove_dead_proxy(proxy)
            attempts += 1
        except Exception as e:
            logging.error(f"Exception during view attempt: {e}", exc_info=True)
            remove_dead_proxy(proxy)
            attempts += 1
    logging.error(f"All proxy attempts failed for this view.")

def main():
    logging.info("Loading proxies...")
    if not proxies:
        logging.critical("No proxies loaded. Please ensure proxies_quality.json or proxies.txt exists.")
        return
    
    url = input("URL: ")

    try:
        amount = int(input("Amount of Views: "))
    except ValueError:
        logging.warning("Failed to give valid number: defaulting to 500")
        amount = 500

    try:
        maxWorkers = int(input("Max Workers: "))
    except ValueError:
        logging.warning("Failed to give valid number: defaulting to 500")
        maxWorkers = 500
    
    with ThreadPoolExecutor(max_workers=maxWorkers) as executor:
        for i in range(amount):
            logging.debug(f"Submitting view {i + 1} of {amount}")
            executor.submit(view_item, url)

if __name__ == "__main__":
    main()
