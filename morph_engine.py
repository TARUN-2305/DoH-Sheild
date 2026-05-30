# morph_engine.py
import joblib
import numpy as np
import os
import secrets

class MorphEngine:
    def __init__(self, model_path='cluster_model.pkl', scaler_path='cluster_scaler.pkl', centroids_path='centroids.npy', epsilon=1.0):
        # Support fallback paths in the current workspace directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        def resolve_path(p):
            if os.path.exists(p):
                return p
            local_p = os.path.join(base_dir, p)
            if os.path.exists(local_p):
                return local_p
            return p
            
        model_path = resolve_path(model_path)
        scaler_path = resolve_path(scaler_path)
        centroids_path = resolve_path(centroids_path)
        
        # Suppress sklearn unpickling warnings
        import warnings
        from sklearn.exceptions import InconsistentVersionWarning
        warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
        
        self.km = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.centroids = np.load(centroids_path)
        self.epsilon = epsilon
        self.sensitivity = 0.1  # Timing sensitivity in seconds
        
    def assign_cluster(self, features):
        """Scale features and assign to the nearest K-Means cluster"""
        scaled = self.scaler.transform(features.reshape(1, -1))
        cluster_id = self.km.predict(scaled)[0]
        return int(cluster_id)
        
    def randomized_cluster(self, features, session_key):
        """Adaptive session-key cluster randomization to prevent static target training"""
        cluster_id = self.assign_cluster(features)
        # Deterministically but unpredictably offset cluster using session key
        # Offset range: [-1, 0, 1]
        offset = (int.from_bytes(session_key[:2], 'big') % 3) - 1
        new_cluster = (cluster_id + offset) % self.km.n_clusters
        return int(new_cluster)
        
    def get_laplace_noise(self, size=1):
        """Generate Differential Privacy Laplace noise"""
        scale = self.sensitivity / self.epsilon
        return np.random.laplace(0.0, scale, size)
        
    def compute_morph_plan(self, current_features, session_key=None):
        """
        Computes the target cluster, the number of dummy packets to inject,
        their padded sizes, and the Laplace-noised timing delays.
        """
        if session_key is None:
            session_key = secrets.token_bytes(32)
            
        target_cluster = self.randomized_cluster(current_features, session_key)
        target_centroid_scaled = self.centroids[target_cluster]
        
        # Inverse-transform target centroid to raw feature space
        target_raw = self.scaler.inverse_transform(target_centroid_scaled.reshape(1, -1))[0]
        
        # FlowBytesSent (index 1) and FlowBytesReceived (index 3)
        curr_sent_bytes = current_features[1]
        curr_received_bytes = current_features[3]
        
        targ_sent_bytes = target_raw[1]
        targ_received_bytes = target_raw[3]
        
        # Target packet length mode (index 9)
        target_mode_size = max(68, int(target_raw[9]))
        
        # Compute bandwidth gap to centroid
        sent_gap = max(0.0, targ_sent_bytes - curr_sent_bytes)
        received_gap = max(0.0, targ_received_bytes - curr_received_bytes)
        
        # Compute number of dummies to inject
        if target_mode_size > 0:
            num_dummies = int(np.ceil(sent_gap / target_mode_size))
        else:
            num_dummies = 0
            
        # Bounded between 0 and 40 queries to avoid network hogging
        num_dummies = min(max(0, num_dummies), 40)
        
        # Generate DP noised timing gaps
        # Base inter-packet gap of 50ms to match real-time queries
        base_gaps = np.full(max(1, num_dummies), 0.05)
        noised_gaps = base_gaps + self.get_laplace_noise(len(base_gaps))
        
        # Clip gaps to ensure no negative values and prevent excessive stalling
        noised_gaps = np.clip(noised_gaps, 0.01, 1.5)
        
        # Attacker Accuracy Upper Bound: P_attack <= 1/k_min + exp(-epsilon)
        # Minimum cluster size from Phase 2 audit = 343
        k_min = 343
        theoretical_bound = (1.0 / k_min) + np.exp(-self.epsilon)
        
        return {
            'target_cluster': target_cluster,
            'num_dummies': num_dummies,
            'dummy_size': target_mode_size,
            'timing_gaps': list(noised_gaps),
            'theoretical_bound': theoretical_bound,
            'sent_gap': sent_gap,
            'received_gap': received_gap
        }

if __name__ == "__main__":
    # Quick self-test
    from feature_extractor import extract_features
    mock_packets = [
        {'timestamp': 100.0, 'size': 68, 'direction': 'out'},
        {'timestamp': 100.1, 'size': 1200, 'direction': 'in'},
    ]
    feats = extract_features(mock_packets)
    
    engine = MorphEngine()
    plan = engine.compute_morph_plan(feats)
    print("Morph Plan computed successfully:")
    print("  Target Cluster:", plan['target_cluster'])
    print("  Dummies needed:", plan['num_dummies'])
    print("  Dummy size:", plan['dummy_size'])
    print("  First 3 timing gaps:", plan['timing_gaps'][:3])
    print("  Theoretical Privacy Bound:", f"{plan['theoretical_bound'] * 100:.2f}%")
