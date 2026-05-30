"""
AI Predictor for Ball-by-Ball Simulation.
Exposes the trained PyTorch neural network to the simulator engine.
"""

import os
import logging
import numpy as np
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

try:
    import torch
    from torch.nn.functional import softmax
    from .train import BallPredictorNet
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. AI Predictor will fall back to heuristic models.")

class AIPredictor:
    """
    Loads the trained PyTorch model and provides fast inference for the simulator.
    """
    
    def __init__(self):
        self.model = None
        self.is_loaded = False
        
        if TORCH_AVAILABLE:
            self._load_model()
            
    def _load_model(self):
        """Loads the saved PyTorch model weights."""
        model_path = os.path.join(os.path.dirname(__file__), "models", "ball_predictor.pth")
        
        if not os.path.exists(model_path):
            logger.warning(f"AI model not found at {model_path}. Run 'ai-train' first.")
            return
            
        try:
            self.model = BallPredictorNet()
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()  # Set to inference mode
            self.is_loaded = True
            logger.info("Successfully loaded PyTorch BallPredictorNet.")
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            
    def predict_ball(self, bat_avg: float, bat_sr: float, bat_form: float,
                    bowl_avg: float, bowl_econ: float, bowl_form: float,
                    match_format: float, pitch_factor: float) -> np.ndarray:
        """
        Predicts the probability distribution for the next ball.
        
        Args:
            bat_avg: Batsman batting average
            bat_sr: Batsman strike rate
            bat_form: Batsman recent form (0.0 to 1.0)
            bowl_avg: Bowler bowling average
            bowl_econ: Bowler economy
            bowl_form: Bowler recent form (0.0 to 1.0)
            match_format: 0.0 (Test), 0.5 (ODI), or 1.0 (T20)
            pitch_factor: ~1.0
            
        Returns:
            Numpy array of 7 probabilities: [Wicket, Dot, 1, 2, 3, 4, 6]
        """
        if not self.is_loaded:
            # Fallback if model not trained
            return np.array([0.05, 0.45, 0.30, 0.05, 0.01, 0.10, 0.04])
            
        # Format inputs into a tensor
        x = torch.tensor([[
            bat_avg / 100.0,
            bat_sr / 200.0,
            bat_form,
            bowl_avg / 100.0,
            bowl_econ / 12.0,
            bowl_form,
            match_format,
            pitch_factor
        ]], dtype=torch.float32)
        
        # Inference
        with torch.no_grad():
            logits = self.model(x)
            probs = softmax(logits, dim=1).numpy().flatten()
            
        return probs