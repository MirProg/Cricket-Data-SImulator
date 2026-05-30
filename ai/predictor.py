import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DeepCricketTransformer(nn.Module):
    def __init__(self, d_model=128, nhead=4, num_layers=2):
        super().__init__()
        # 12 context features: bat_avg, bat_sr, bat_form, bowl_avg, bowl_econ, bowl_form, 
        # format_enc, pitch, score, wickets, overs, target
        self.input_proj = nn.Linear(12, d_model)
        
        # Add a mock sequence processor for the " हजारों (thousands of)" factor context
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=d_model*4, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc1 = nn.Linear(d_model, d_model * 2)
        self.dropout = nn.Dropout(0.2)
        self.fc2 = nn.Linear(d_model * 2, d_model)
        
        # 7 output classes: WICKET(0), DOT(1), 1(2), 2(3), 3(4), 4(5), 6(6)
        self.out = nn.Linear(d_model, 7)
        
    def forward(self, x):
        # x shape: (batch, seq_len, 12)
        x = self.input_proj(x)
        x = self.transformer(x)
        # Take the last sequence element
        x = x[:, -1, :]
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        return self.out(x)

class AIPredictor:
    def __init__(self, model_path=None):
        if not model_path:
            model_path = os.path.join(os.path.dirname(__file__), 'models', 'advanced_predictor.pth')
        
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = DeepCricketTransformer().to(self.device)
        self.is_loaded = False
        self._load_model()
        
    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.model.eval()
                self.is_loaded = True
                logger.info("Successfully loaded Advanced PyTorch Transformer.")
            else:
                logger.warning(f"Advanced model not found at {self.model_path}. Fallback to heuristics.")
        except Exception as e:
            logger.error(f"Failed to load Advanced model: {e}")
            
    def predict_ball(self, bat_avg, bat_sr, bat_form, bowl_avg, bowl_econ, bowl_form, match_format, pitch_factor, 
                     score=0, wickets=0, overs=0, target=0):
        if not self.is_loaded:
            return None
            
        # Build state context
        # In a real seq model, we'd pass a sequence of past balls. Here we pass a single element sequence.
        context = [
            bat_avg / 50.0,
            bat_sr / 150.0,
            bat_form,
            bowl_avg / 40.0,
            bowl_econ / 10.0,
            bowl_form,
            match_format,
            pitch_factor,
            score / 300.0,
            wickets / 10.0,
            overs / 50.0,
            target / 300.0
        ]
        
        tensor_in = torch.tensor([[context]], dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            logits = self.model(tensor_in)
            probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
            
        return probs