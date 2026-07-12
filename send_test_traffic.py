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

def send_burst():
    main_site = random.choice(SITES)
    # Generate 5 realistic DoH requests for resources/sub-domains to simulate a real page burst
    sub_sites = [
        main_site, 
        f"www.{main_site}", 
        f"api.{main_site}", 
        f"static.{main_site}", 
        f"assets.{main_site}"
    ]
    
    print(f"[*] Simulating site burst for: {main_site} ({len(sub_sites)} queries)...")
    
    headers = {
        'Content-Type': 'application/dns-message',
        'Accept': 'application/dns-message',
        'Connection': 'close',
        'User-Agent': 'DoH-Shield-Test-Client/1.0'
    }
    
    try:
        with httpx.Client(proxy=PROXY, verify=False, timeout=5.0) as client:
            for site in sub_sites:
                msg = dns.message.make_query(site, dns.rdatatype.A)
                wire_data = msg.to_wire()
                
                start_time = time.time()
                resp = client.post(RESOLVER_URL, content=wire_data, headers=headers)
                elapsed = time.time() - start_time
                print(f"   [+] Sent {site} -> Status: {resp.status_code}, Time: {elapsed:.2f}s")
                
                # Tiny gap between sub-queries to simulate realistic browser scheduling
                time.sleep(random.uniform(0.05, 0.15))
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
            send_burst()
            # Wait 3.5 seconds (allowing the 2.0s proxy inactivity timeout to flush the burst session)
            sleep_time = 3.5
            print(f"[*] Sleeping for {sleep_time}s...")
            time.sleep(sleep_time)
            print()
    except KeyboardInterrupt:
        print("\n[+] Stopped traffic generation. Goodbye!")

if __name__ == "__main__":
    main()
