# verify_shield.py
import unittest
import numpy as np
import os
from feature_extractor import extract_features
from morph_engine import MorphEngine
from dummy_injector import build_padded_query

class TestDoHShield(unittest.TestCase):
    
    def test_feature_extractor(self):
        """1. Validate feature extractor on mock packet flows"""
        mock_packets = [
            {'timestamp': 100.0, 'size': 68, 'direction': 'out'},
            {'timestamp': 100.1, 'size': 1200, 'direction': 'in'},
            {'timestamp': 101.0, 'size': 68, 'direction': 'out'},
            {'timestamp': 101.2, 'size': 1500, 'direction': 'in'},
        ]
        feats = extract_features(mock_packets)
        self.assertEqual(feats.shape, (29,))
        self.assertAlmostEqual(feats[0], 1.2)  # Duration (101.2 - 100.0)
        self.assertEqual(feats[1], 136.0)     # FlowBytesSent (68 * 2)
        self.assertEqual(feats[3], 2700.0)    # FlowBytesReceived (1200 + 1500)
        self.assertGreater(feats[7], 0.0)      # PacketLengthMean should be > 0
        
    def test_morph_engine(self):
        """2. Validate MorphEngine model loading, cluster assignment, and morph plans"""
        engine = MorphEngine()
        self.assertIsNotNone(engine.km)
        self.assertIsNotNone(engine.scaler)
        self.assertIsNotNone(engine.centroids)
        
        # Test compute morph plan on typical values
        mock_features = np.zeros(29)
        mock_features[1] = 500.0   # FlowBytesSent
        mock_features[3] = 1000.0  # FlowBytesReceived
        
        plan = engine.compute_morph_plan(mock_features)
        
        self.assertIn('target_cluster', plan)
        self.assertIn('num_dummies', plan)
        self.assertIn('dummy_size', plan)
        self.assertIn('timing_gaps', plan)
        self.assertGreaterEqual(plan['num_dummies'], 0)
        self.assertGreaterEqual(plan['dummy_size'], 68)
        self.assertGreater(plan['theoretical_bound'], 0.0)
        self.assertLessEqual(plan['theoretical_bound'], 1.0)
        
    def test_laplace_noise(self):
        """3. Validate Laplace noise distribution properties (mean ~ 0)"""
        engine = MorphEngine(epsilon=1.0)
        noise = engine.get_laplace_noise(10000)
        self.assertEqual(len(noise), 10000)
        # For Lap(0, scale) with scale = 0.1/1.0 = 0.1:
        # Sample mean should be extremely close to 0 (tolerance delta = 0.01)
        self.assertAlmostEqual(np.mean(noise), 0.0, delta=0.01)
        
    def test_dummy_padding(self):
        """4. Validate EDNS(0) padded DNS query wire size correctness"""
        # Test multiple target sizes (e.g. 68, 100, 150 bytes)
        for size in [68, 100, 150, 200]:
            wire = build_padded_query("dummy.test", size)
            self.assertEqual(len(wire), size, f"Failed EDNS padding size check for {size} bytes")

if __name__ == "__main__":
    unittest.main()
