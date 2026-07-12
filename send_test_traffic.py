# send_test_traffic.py
import time
import random
import base64
import sys
import httpx
import dns.message
import dns.rdatatype

# Force UTF-8 encoding for standard output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SITES = [
    "google.com", "youtube.com", "facebook.com", "wikipedia.org",
    "github.com", "reddit.com" 
]

PROXY = "http://127.0.0.1:8080"
RESOLVER_URL = "https://cloudflare-dns.com/dns-query"

def send_request():
    site = random.choice(SITES)
    print(f"[*] Crafting query for: {site}")
    
    # Create DNS A query
    msg = dns.message.make_query(site, dns.rdatatype.A)
    wire_data = msg.to_wire()
    
    # Base64url encode for GET dns parameter
    b64_query = base64.urlsafe_b64encode(wire_data).decode('utf-8').rstrip('=')
    url = f"{RESOLVER_URL}?dns={b64_query}"
    
    headers = {
        "Connection": "close",
        "User-Agent": "DoH-Shield-Test-Client/1.0"
    }
    try:
        with httpx.Client(proxy=PROXY, verify=False, timeout=5.0) as client:
            start_time = time.time()
            resp = client.get(url, headers=headers)
            elapsed = time.time() - start_time
            print(f"   [+] Sent through proxy -> Status: {resp.status_code}, Time: {elapsed:.2f}s")
    except Exception as e:
        print(f"   [!] Request failed (is the proxy running on 8080?): {e}")

def main():
    print("==================================================")
    print("🛡️  D O H - S H I E L D   T R A F F I C   G E N  🛡️")
    print("==================================================")
    print(f"Proxy Target: {PROXY}")
    print("Press Ctrl+C to stop.")
    print("==================================================")
    
    # Suppress warning messages about insecure requests (verify=False)
    import warnings
    warnings.filterwarnings("ignore")
    
    try:
        while True:
            send_request()
            # Wait 2.5 seconds (just above the 2.0s proxy idle timeout) to force separate, faster sessions
            sleep_time = 2.5
            print(f"[*] Sleeping for {sleep_time}s...")
            time.sleep(sleep_time)
            print()
    except KeyboardInterrupt:
        print("\n[+] Stopped traffic generation. Goodbye!")

if __name__ == "__main__":
    main()
