# mock_doh_resolver.py
# A simple HTTP server acting as a mock DNS-over-HTTPS (DoH) resolver on port 8081.

import http.server
import socketserver
import dns.message
import dns.rdatatype
import sys

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8081

class MockDoHHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging to keep console clean
        pass

    def do_POST(self):
        if self.path == '/dns-query':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                # Parse the incoming DNS query
                query = dns.message.from_wire(body)
                domain = query.question[0].name.to_text()
                print(f"[Mock Resolver] Received query for {domain}", flush=True)
                
                # Craft a mock DNS response
                response = dns.message.make_response(query)
                # Add a dummy A record answer
                rrset = dns.rrset.from_text(query.question[0].name, 300, dns.rdataclass.IN, dns.rdatatype.A, '127.0.0.99')
                response.answer.append(rrset)
                
                response_data = response.to_wire()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/dns-message')
                self.send_header('Content-Length', str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data)
                return
            except Exception as e:
                print(f"[Mock Resolver] Error parsing query: {e}", flush=True)
                
        self.send_response(400)
        self.end_headers()

    def do_GET(self):
        # Support GET DoH queries (sent in base64url parameter)
        if self.path.startswith('/dns-query'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/dns-message')
            # Send an empty response or a generic response
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

def main():
    # Allow port reuse to avoid address already in use errors
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), MockDoHHandler) as httpd:
        print(f"🚀 Mock DoH Resolver running on http://127.0.0.1:{PORT}/dns-query", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Mock DoH Resolver...", flush=True)

if __name__ == "__main__":
    main()
