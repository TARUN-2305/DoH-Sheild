# dummy_injector.py
import asyncio
import httpx
import secrets
import dns.message
import dns.rdatatype
import dns.edns

def build_padded_query(domain, target_size=68):
    """
    Crafts a standard DNS A query and pads it to target_size using EDNS(0) padding.
    """
    msg = dns.message.make_query(domain, dns.rdatatype.A)
    msg.use_edns()
    wire = msg.to_wire()
    current_len = len(wire)
    
    if target_size > current_len + 4:
        padding_len = target_size - current_len - 4
        pad_opt = dns.edns.GenericOption(12, b'\x00' * padding_len)
        msg.use_edns(options=[pad_opt])
        
    return msg.to_wire()

async def send_dummy_request(target_size, resolver_url='https://cloudflare-dns.com/dns-query'):
    """
    Sends a single padded dummy DNS query to the DoH resolver.
    """
    # Unique sub-domain ensures Cloudflare has to perform resolution (NXDOMAIN)
    # and prevents standard DNS cache serving
    rand_id = secrets.token_hex(4)
    domain = f"dohshield-dummy-{rand_id}.test"
    
    query_data = build_padded_query(domain, target_size)
    
    headers = {
        'Content-Type': 'application/dns-message',
        'Accept': 'application/dns-message',
        'User-Agent': 'DoH-Shield-Proxy/1.0'
    }
    
    try:
        # We run with a short timeout; if a dummy fails, we don't care.
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(resolver_url, content=query_data, headers=headers)
            return resp.status_code, len(resp.content)
    except Exception:
        return 0, 0

async def inject_dummies(count, target_size, timing_gaps, resolver_url='https://cloudflare-dns.com/dns-query'):
    """
    Asynchronously schedules count dummy requests separated by the specified timing gaps.
    """
    for i in range(count):
        gap = timing_gaps[i] if i < len(timing_gaps) else 0.05
        await asyncio.sleep(gap)
        # Schedule in the background (fire-and-forget)
        asyncio.create_task(send_dummy_request(target_size, resolver_url))

if __name__ == "__main__":
    # Test script to send a single padded query
    async def main():
        print("Sending test padded query...")
        status, resp_len = await send_dummy_request(128)
        print(f"Result: HTTP {status}, Response Size: {resp_len} bytes")
        
    asyncio.run(main())
