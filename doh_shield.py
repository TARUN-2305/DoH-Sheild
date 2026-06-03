# doh_shield.py
import sys

# Force UTF-8 encoding for standard output/error on Windows environments
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import time
import json
import os
import secrets
import threading
from mitmproxy import http
import dns.message
import dns.rdatatype

from feature_extractor import extract_features
from morph_engine import MorphEngine
from dummy_injector import inject_dummies

class DoHShieldAddon:
    def __init__(self):
        self.engine = MorphEngine()
        self.sessions = {}  # conn_id -> session dict
        self.stats = {
            'active_sessions': 0,
            'total_queries': 0,
            'total_dummies': 0,
            'total_original_bytes': 0,
            'total_dummy_bytes': 0,
            'history': []
        }
        self.lock = threading.Lock()
        self.stats_file = 'stats.json'
        
        self.save_stats()
        print("🛡️ DoH-Shield Addon Initialized! Listening for DoH traffic...")

    def running(self):
        print("🚀 DoH-Shield running hook called!")
        # Start the idle checker loop in the background once mitmproxy is running
        asyncio.create_task(self.check_idle_sessions_loop())

    def save_stats(self):
        """Atomically saves current stats to stats.json for the dashboard to read"""
        with self.lock:
            try:
                temp_file = self.stats_file + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(self.stats, f, indent=2)
                os.replace(temp_file, self.stats_file)
            except Exception as e:
                print(f"Error saving stats: {e}")

    def request(self, flow: http.HTTPFlow):
        # Only intercept DoH requests to Cloudflare or Google
        if 'cloudflare-dns.com' in flow.request.pretty_host or 'dns.google' in flow.request.pretty_host:
            # Redirect request to the local mock resolver on port 8081
            flow.request.host = "127.0.0.1"
            flow.request.port = 8081
            flow.request.scheme = "http"
            
            conn_id = flow.client_conn.id
            ts = time.time()
            content = flow.request.content or b''
            
            # If content is empty and it's a GET request, check the dns query parameter
            if not content and flow.request.method == 'GET':
                dns_param = flow.request.query.get('dns')
                if dns_param:
                    import base64
                    dns_param += '=' * (-len(dns_param) % 4)
                    try:
                        content = base64.urlsafe_b64decode(dns_param)
                    except Exception:
                        pass
                        
            sz = len(content)
            
            # Parse requested domain name for visualization/dashboard
            domain = "Unknown"
            try:
                dns_msg = dns.message.from_wire(content)
                if dns_msg.question:
                    domain = dns_msg.question[0].name.to_text().rstrip('.')
            except Exception:
                pass
                
            with self.lock:
                if conn_id not in self.sessions:
                    self.sessions[conn_id] = {
                        'packets': [],
                        'response_times': [],
                        'domains': set(),
                        'last_activity': ts,
                        'session_key': secrets.token_bytes(32),
                        'start_time': ts
                    }
                
                self.sessions[conn_id]['packets'].append({
                    'timestamp': ts,
                    'size': sz,
                    'direction': 'out'
                })
                self.sessions[conn_id]['domains'].add(domain)
                self.sessions[conn_id]['last_activity'] = ts
                self.stats['total_queries'] += 1
                self.stats['total_original_bytes'] += sz
                self.stats['active_sessions'] = len(self.sessions)
                
            self.save_stats()

    def response(self, flow: http.HTTPFlow):
        conn_id = flow.client_conn.id
        with self.lock:
            in_session = conn_id in self.sessions
            
        if in_session:
            ts = time.time()
            content = flow.response.content or b''
            sz = len(content)
            
            with self.lock:
                if conn_id in self.sessions:
                    session = self.sessions[conn_id]
                    session['packets'].append({
                        'timestamp': ts,
                        'size': sz,
                        'direction': 'in'
                    })
                    # Measure transaction latency
                    req_packets = [p for p in session['packets'] if p['direction'] == 'out']
                    if req_packets:
                        latency = ts - req_packets[-1]['timestamp']
                        session['response_times'].append(latency)
                        
                    session['last_activity'] = ts
                    self.stats['total_original_bytes'] += sz
                    
            self.save_stats()

    async def check_idle_sessions_loop(self):
        """Periodically runs to check for idle DNS burst flows and trigger morphing"""
        print("🔍 check_idle_sessions_loop started!")
        while True:
            await asyncio.sleep(0.5)
            now = time.time()
            to_morph = []
            
            with self.lock:
                if self.sessions:
                    print(f"DEBUG: {len(self.sessions)} active sessions", flush=True)
                    for cid, s in self.sessions.items():
                        print(f"  session {cid[:8] if cid else 'None'}: packets={len(s['packets'])}, idle={now - s['last_activity']:.1f}s", flush=True)
                for conn_id, session in list(self.sessions.items()):
                    # If inactive for >= 2.0 seconds and has accumulated queries
                    if now - session['last_activity'] >= 2.0 and len(session['packets']) >= 2:
                        to_morph.append((conn_id, session))
                        del self.sessions[conn_id]
                
                self.stats['active_sessions'] = len(self.sessions)
                
            # Perform morphing outside of lock
            try:
                for conn_id, session in to_morph:
                    await self.morph_session(conn_id, session)
                if to_morph:
                    self.save_stats()
            except Exception as e:
                import traceback
                print(f"❌ Exception in check_idle_sessions_loop morphing: {e}", flush=True)
                traceback.print_exc()

            if not hasattr(self, '_loop_counter'):
                self._loop_counter = 0
            self._loop_counter += 1
            if self._loop_counter % 10 == 0:
                print(f"DEBUG: loop heartbeat {self._loop_counter // 10}", flush=True)

    async def morph_session(self, conn_id, session):
        """Extracts features, runs the morph engine, and schedules dummy injections"""
        packets = session['packets']
        rt = session['response_times']
        domains = list(session['domains'])
        domain_display = domains[0] if domains else "Unknown"
        if len(domains) > 1:
            domain_display += f" (+{len(domains)-1} others)"
            
        print(f"\n🔮 Flow Inactivity Detected! Morphing session {conn_id[:8]} ({domain_display})...", flush=True)
        
        # 1. Feature Extraction
        features = extract_features(packets, rt)
        
        # 2. Cluster & Morph Plan
        plan = self.engine.compute_morph_plan(features, session['session_key'])
        
        target_cluster = plan['target_cluster']
        num_dummies = plan['num_dummies']
        dummy_size = plan['dummy_size']
        gaps = plan['timing_gaps']
        bound = plan['theoretical_bound']
        
        print(f"  -> Extracted features. Original Bytes: {int(features[1] + features[3])} B", flush=True)
        print(f"  -> Assigned Target Cluster: {target_cluster}", flush=True)
        print(f"  -> Injecting {num_dummies} dummy queries of size {dummy_size} bytes...", flush=True)
        
        # 3. Dummy Injection (Async fire-and-forget)
        if num_dummies > 0:
            await inject_dummies(num_dummies, dummy_size, gaps, resolver_url='http://127.0.0.1:8081/dns-query')
            
            with self.lock:
                self.stats['total_dummies'] += num_dummies
                # Total bytes sent = dummies * dummy_size
                # Total bytes received is estimated based on dummy NXDOMAIN size (approx. 150 bytes per query)
                dummy_bytes = num_dummies * (dummy_size + 150)
                self.stats['total_dummy_bytes'] += dummy_bytes
        
        # Compute bandwidth overhead percentage
        total_original = features[1] + features[3]
        total_dummy = num_dummies * (dummy_size + 150) if num_dummies > 0 else 0
        overhead_pct = (total_dummy / total_original * 100.0) if total_original > 0 else 0.0
        
        # 4. Save to History for Dashboard
        history_item = {
            'timestamp': time.strftime('%H:%M:%S'),
            'domain': domain_display,
            'queries': len([p for p in packets if p['direction'] == 'out']),
            'original_bytes': int(total_original),
            'target_cluster': target_cluster,
            'dummies_injected': num_dummies,
            'dummy_size': dummy_size,
            'overhead_pct': round(overhead_pct, 1),
            'privacy_bound': round(bound * 100.0, 2)
        }
        
        with self.lock:
            self.stats['history'].append(history_item)
            # Keep history to last 10 entries
            if len(self.stats['history']) > 10:
                self.stats['history'].pop(0)

# Wire addon to mitmproxy
addons = [DoHShieldAddon()]
