# feature_extractor.py
import numpy as np
from collections import Counter

def extract_features(packets, response_times=None):
    """
    Extracts 29 statistical features from a list of packet events.
    
    packets: list of dicts, each having:
             - 'timestamp': float (absolute time in seconds)
             - 'size': int (bytes)
             - 'direction': 'in' (received) or 'out' (sent)
    response_times: optional list of float latencies for request-response pairs.
                    If not provided, they will be matched chronologically.
    """
    if not packets:
        return np.zeros(29)
    
    # Sort packets chronologically
    packets = sorted(packets, key=lambda p: p['timestamp'])
    
    timestamps = [p['timestamp'] for p in packets]
    sizes = [p['size'] for p in packets]
    
    t_min = timestamps[0]
    duration = timestamps[-1] - t_min
    
    out_packets = [p for p in packets if p['direction'] == 'out']
    in_packets = [p for p in packets if p['direction'] == 'in']
    
    flow_bytes_sent = sum(p['size'] for p in out_packets)
    flow_bytes_received = sum(p['size'] for p in in_packets)
    
    flow_sent_rate = flow_bytes_sent / duration if duration > 0 else 0.0
    flow_received_rate = flow_bytes_received / duration if duration > 0 else 0.0
    
    # Helper for statistical features
    def get_stats(vals):
        if not vals:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        arr = np.array(vals, dtype=float)
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        var = float(np.var(arr))
        median = float(np.median(arr))
        
        # Mode calculation (smallest mode if multiple exist)
        c = Counter(vals)
        most_common = c.most_common()
        max_freq = most_common[0][1]
        modes = [item for item, freq in most_common if freq == max_freq]
        mode = float(min(modes))
        
        # Pearson's Skewness coefficients
        skew_median = 3.0 * (mean - median) / std if std > 0.0 else 0.0
        skew_mode = (mean - mode) / std if std > 0.0 else 0.0
        
        # Coefficient of variation
        cov = std / mean if mean > 0.0 else 0.0
        
        return var, std, mean, median, mode, skew_median, skew_mode, cov

    # Packet Length stats
    p_len_var, p_len_std, p_len_mean, p_len_median, p_len_mode, p_len_skew_median, p_len_skew_mode, p_len_cov = get_stats(sizes)
    
    # Packet Time stats (relative timestamps)
    rel_times = [t - t_min for t in timestamps]
    p_time_var, p_time_std, p_time_mean, p_time_median, p_time_mode, p_time_skew_median, p_time_skew_mode, p_time_cov = get_stats(rel_times)
    
    # Response Time stats
    if response_times is None:
        response_times = []
        in_idx = 0
        for out_p in out_packets:
            # Match with the first available 'in' packet that occurs after the request
            while in_idx < len(in_packets) and in_packets[in_idx]['timestamp'] < out_p['timestamp']:
                in_idx += 1
            if in_idx < len(in_packets):
                response_times.append(in_packets[in_idx]['timestamp'] - out_p['timestamp'])
                in_idx += 1 # Consume this response
                
    rt_var, rt_std, rt_mean, rt_median, rt_mode, rt_skew_median, rt_skew_mode, rt_cov = get_stats(response_times)
    
    features = [
        duration,
        flow_bytes_sent,
        flow_sent_rate,
        flow_bytes_received,
        flow_received_rate,
        p_len_var,
        p_len_std,
        p_len_mean,
        p_len_median,
        p_len_mode,
        p_len_skew_median,
        p_len_skew_mode,
        p_len_cov,
        p_time_var,
        p_time_std,
        p_time_mean,
        p_time_median,
        p_time_mode,
        p_time_skew_median,
        p_time_skew_mode,
        p_time_cov,
        rt_var,
        rt_std,
        rt_mean,
        rt_median,
        rt_mode,
        rt_skew_median,
        rt_skew_mode,
        rt_cov
    ]
    
    return np.array(features, dtype=float)

if __name__ == "__main__":
    # Quick self-test
    mock_packets = [
        {'timestamp': 100.0, 'size': 68, 'direction': 'out'},
        {'timestamp': 100.1, 'size': 1500, 'direction': 'in'},
        {'timestamp': 101.0, 'size': 68, 'direction': 'out'},
        {'timestamp': 101.2, 'size': 1000, 'direction': 'in'},
    ]
    feats = extract_features(mock_packets)
    print("Extracted Features Shape:", feats.shape)
    print("Duration:", feats[0])
    print("FlowBytesSent:", feats[1])
    print("FlowBytesReceived:", feats[3])
    print("PacketLengthMean:", feats[7])
    print("PacketLengthMode:", feats[9])
    print("PacketTimeMean:", feats[15])
    print("ResponseTimeMean:", feats[23])
