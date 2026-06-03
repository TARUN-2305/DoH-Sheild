# web_server.py
# A lightweight Flask server serving the DoH-Shield interactive simulation web portal on port 8082.

import os
import json
import time
import sys
import numpy as np
from flask import Flask, request, jsonify, send_from_directory

# Force UTF-8 encoding for stdout/stderr to avoid Windows CP1252 crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from feature_extractor import extract_features
from morph_engine import MorphEngine

app = Flask(__name__, static_folder='web_frontend')

# Preset browser traffic profiles for simulation
PRESET_SCENARIOS = {
    "single": [
        {'timestamp': 0.0, 'size': 68, 'direction': 'out'},
        {'timestamp': 0.05, 'size': 150, 'direction': 'in'}
    ],
    "burst": [
        {'timestamp': 0.0, 'size': 72, 'direction': 'out'},
        {'timestamp': 0.04, 'size': 512, 'direction': 'in'},
        {'timestamp': 0.12, 'size': 68, 'direction': 'out'},
        {'timestamp': 0.18, 'size': 1200, 'direction': 'in'},
        {'timestamp': 0.22, 'size': 85, 'direction': 'out'},
        {'timestamp': 0.25, 'size': 1100, 'direction': 'in'},
        {'timestamp': 0.45, 'size': 68, 'direction': 'out'},
        {'timestamp': 0.51, 'size': 1500, 'direction': 'in'},
        {'timestamp': 0.70, 'size': 74, 'direction': 'out'},
        {'timestamp': 0.73, 'size': 250, 'direction': 'in'},
    ],
    "tunnel": [
        {'timestamp': i * 0.1, 'size': 180, 'direction': 'out'} for i in range(15)
    ] + [
        {'timestamp': i * 0.1 + 0.02, 'size': 180, 'direction': 'in'} for i in range(15)
    ]
}

@app.route('/')
def index():
    return send_from_directory('web_frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('web_frontend', path)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Reads the local stats.json file and returns its content"""
    stats_file = 'stats.json'
    if not os.path.exists(stats_file):
        return jsonify({
            'active_sessions': 0,
            'total_queries': 0,
            'total_dummies': 0,
            'total_original_bytes': 0,
            'total_dummy_bytes': 0,
            'history': []
        })
    try:
        with open(stats_file, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    Receives parameters:
    - epsilon (float)
    - sensitivity (float)
    - scenario (string: 'single', 'burst', 'tunnel')
    
    Runs feature extraction, KMeans cluster assignment, and calculates the morphing plan.
    Generates original and morphed timelines for comparison on the frontend.
    """
    data = request.json or {}
    epsilon = float(data.get('epsilon', 1.0))
    sensitivity = float(data.get('sensitivity', 0.1))
    scenario = data.get('scenario', 'single')
    
    if scenario not in PRESET_SCENARIOS:
        return jsonify({'error': 'Invalid scenario preset'}), 400
        
    raw_packets = PRESET_SCENARIOS[scenario]
    
    # 1. Feature Extraction
    features = extract_features(raw_packets)
    
    # 2. Instantiate MorphEngine and compute plan
    try:
        engine = MorphEngine(epsilon=epsilon)
        engine.sensitivity = sensitivity
        plan = engine.compute_morph_plan(features)
    except Exception as e:
        return jsonify({'error': f"Failed to run MorphEngine: {str(e)}"}), 500
        
    target_cluster = plan['target_cluster']
    num_dummies = plan['num_dummies']
    dummy_size = plan['dummy_size']
    timing_gaps = plan['timing_gaps']
    theoretical_bound = plan['theoretical_bound']
    
    # 3. Create the comparative timeline
    original_timeline = []
    morphed_timeline = []
    
    # Copy original packets (sorted chronologically)
    sorted_raw = sorted(raw_packets, key=lambda p: p['timestamp'])
    for p in sorted_raw:
        original_timeline.append({
            'time': round(p['timestamp'], 3),
            'size': p['size'],
            'direction': p['direction'],
            'type': 'original'
        })
    
    # Compute morphed timeline:
    # - Original packets are copied, but response packets ('in') get delayed by Laplace noise!
    current_time = 0.0
    for p in sorted_raw:
        p_time = p['timestamp']
        if p['direction'] == 'in':
            # Add timing delay to response packets
            noise = engine.get_laplace_noise(1)[0]
            # Clip delay to avoid negative or excessive values
            noise_delay = min(max(0.01, noise), 1.5)
            p_time += noise_delay
            
        morphed_timeline.append({
            'time': round(p_time, 3),
            'size': p['size'],
            'direction': p['direction'],
            'type': 'original'
        })
        
    # - Inject dummies at the end of the original flow with Laplace timing gaps
    last_packet_time = max([p['time'] for p in morphed_timeline]) if morphed_timeline else 0.0
    current_dummy_time = last_packet_time + 0.1
    for i in range(num_dummies):
        gap = timing_gaps[i] if i < len(timing_gaps) else 0.05
        current_dummy_time += gap
        # Dummy queries are always outgoing ('out')
        morphed_timeline.append({
            'time': round(current_dummy_time, 3),
            'size': dummy_size,
            'direction': 'out',
            'type': 'dummy'
        })
        
    # Sort morphed timeline chronologically
    morphed_timeline = sorted(morphed_timeline, key=lambda p: p['time'])
    
    return jsonify({
        'features': {
            'duration': round(features[0], 3),
            'bytes_sent': int(features[1]),
            'bytes_received': int(features[3])
        },
        'plan': {
            'target_cluster': target_cluster,
            'num_dummies': num_dummies,
            'dummy_size': dummy_size,
            'privacy_bound': round(theoretical_bound * 100.0, 2),
            'overhead_pct': round((num_dummies * (dummy_size + 150)) / (features[1] + features[3]) * 100.0, 1) if (features[1] + features[3]) > 0 else 0.0
        },
        'timelines': {
            'original': original_timeline,
            'morphed': morphed_timeline
        }
    })

def main():
    app.run(host='127.0.0.1', port=8082, debug=False)

if __name__ == '__main__':
    main()
