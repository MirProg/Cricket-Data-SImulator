"""
Deep Learning Training Pipeline for Ball-by-Ball Simulation.
Uses PyTorch to train a Generative AI model that predicts ball outcomes.
"""

import os
import random
import logging
import time
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch is not installed. Please run: pip install torch")

# Event indices
EVENT_WICKET = 0
EVENT_DOT = 1
EVENT_RUN1 = 2
EVENT_RUN2 = 3
EVENT_RUN3 = 4
EVENT_RUN4 = 5
EVENT_SIX = 6

class BallPredictorNet(nn.Module):
    """
    Neural Network that predicts the probability distribution of ball outcomes.
    Inputs (8 features):
        0: Batsman Average
        1: Batsman Strike Rate
        2: Batsman Recent Form
        3: Bowler Average
        4: Bowler Economy
        5: Bowler Recent Form
        6: Match Format (0: Test, 0.5: ODI, 1: T20)
        7: Pitch Factor (0.8 to 1.2)
    Outputs (7 probabilities):
        [Wicket, Dot, 1 Run, 2 Runs, 3 Runs, 4 Runs, 6 Runs]
    """
    def __init__(self):
        super(BallPredictorNet, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(8, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 7)
        )
        
    def forward(self, x):
        # We output logits; CrossEntropyLoss handles softmax during training.
        # During inference, we apply softmax explicitly.
        return self.network(x)


class SyntheticCricketDataset(Dataset):
    """Generates synthetic training data based on realistic cricket statistics."""
    
    def __init__(self, num_samples=100000):
        self.num_samples = num_samples
        self.X = np.zeros((num_samples, 8), dtype=np.float32)
        self.y = np.zeros(num_samples, dtype=np.int64)
        
        self._generate_data()
        
    def _generate_data(self):
        logger.info(f"Generating {self.num_samples} synthetic training samples...")
        
        for i in range(self.num_samples):
            # Generate random realistic stats
            bat_avg = random.uniform(10.0, 60.0)
            bat_sr = random.uniform(60.0, 180.0)
            bat_form = random.uniform(0.0, 1.0)
            
            bowl_avg = random.uniform(15.0, 60.0)
            bowl_econ = random.uniform(4.0, 10.0)
            bowl_form = random.uniform(0.0, 1.0)
            
            match_format = random.choice([0.0, 0.5, 1.0]) # Test, ODI, T20
            pitch_factor = random.uniform(0.8, 1.2) # >1 favors batsman
            
            # Formulate feature vector
            x = np.array([
                bat_avg / 100.0,      # Normalize
                bat_sr / 200.0,       # Normalize
                bat_form,
                bowl_avg / 100.0,     # Normalize
                bowl_econ / 12.0,     # Normalize
                bowl_form,
                match_format,
                pitch_factor
            ], dtype=np.float32)
            
            # Ground truth mathematical heuristic (our "teacher" function)
            probs = self._mathematical_baseline(bat_avg, bat_sr, bowl_avg, bowl_econ, match_format, pitch_factor)
            
            # Sample an outcome based on probabilities to create real "messy" data
            outcome = np.random.choice(7, p=probs)
            
            self.X[i] = x
            self.y[i] = outcome
            
    def _mathematical_baseline(self, bat_avg, bat_sr, bowl_avg, bowl_econ, fmt, pitch):
        """Hidden logic that creates realistic event probabilities for a given matchup."""
        
        # Base probabilities: [Wicket, Dot, 1, 2, 3, 4, 6]
        probs = np.array([0.05, 0.45, 0.30, 0.05, 0.01, 0.10, 0.04])
        
        # Wicket modifications
        wicket_chance = 0.05 * (30.0 / max(bat_avg, 5.0)) * (25.0 / max(bowl_avg, 5.0))
        if fmt == 1.0: # T20
            wicket_chance *= 1.3
        elif fmt == 0.0: # Test
            wicket_chance *= 0.7
            
        probs[EVENT_WICKET] = max(0.01, min(0.25, wicket_chance))
        
        # Aggression metric
        aggression = (bat_sr / 100.0) * (6.0 / max(bowl_econ, 3.0)) * pitch
        if fmt == 1.0: aggression *= 1.5
        if fmt == 0.0: aggression *= 0.6
        
        # Adjust boundaries based on aggression
        probs[EVENT_RUN4] = 0.10 * aggression
        probs[EVENT_SIX] = 0.04 * (aggression ** 1.5)
        
        # Normalize non-wicket events to fill the remaining probability
        remaining_prob = 1.0 - probs[EVENT_WICKET]
        non_wicket_sum = np.sum(probs[1:])
        
        for i in range(1, 7):
            probs[i] = (probs[i] / non_wicket_sum) * remaining_prob
            
        return probs

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def train_ai_model(epochs=10, batch_size=256, samples=200000):
    """Generates data and trains the deep learning model."""
    if not TORCH_AVAILABLE:
        logger.error("Cannot train: PyTorch is not available.")
        return False
        
    print("\n" + "="*50)
    print("🧠 INITIATING AI MODEL TRAINING (PyTorch)")
    print("="*50)
    
    # Generate data
    dataset = SyntheticCricketDataset(num_samples=samples)
    
    # Split into train/val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Print class distribution
    all_y = [y for _, y in train_dataset]
    counts = Counter(all_y)
    print(f"\nTraining Data Distribution:")
    events = ["Wickets", "Dots", "1s", "2s", "3s", "4s", "6s"]
    for i, e in enumerate(events):
        print(f"  {e}: {counts[i] / len(train_dataset):.1%}")
    
    # Initialize model, loss, optimizer
    model = BallPredictorNet()
    
    # Add class weights because wickets and 3s are rare
    weights = torch.tensor([
        len(train_dataset)/counts[0], 
        1.0, 
        1.0, 
        len(train_dataset)/counts[3], 
        len(train_dataset)/max(1, counts[4]), 
        len(train_dataset)/counts[5], 
        len(train_dataset)/counts[6]
    ], dtype=torch.float32)
    # Normalize weights
    weights = weights / weights.sum() * 7.0
    
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.Adam(model.parameters(), lr=0.002)
    
    print(f"\nTraining Neural Network for {epochs} epochs...")
    
    start_time = time.time()
    
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            _, predicted = torch.max(outputs.data, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
            
        train_loss = running_loss / len(train_loader)
        train_acc = 100 * correct / total
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                
                _, predicted = torch.max(outputs.data, 1)
                val_total += batch_y.size(0)
                val_correct += (predicted == batch_y).sum().item()
                
        val_loss = val_loss / len(val_loader)
        val_acc = 100 * val_correct / val_total
        
        print(f"  Epoch [{epoch+1}/{epochs}] - "
              f"Loss: {train_loss:.4f} | Acc: {train_acc:.1f}% | "
              f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.1f}%")

    print(f"\n✅ Training complete in {time.time() - start_time:.1f} seconds")
    
    # Save model
    model_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(model_dir, exist_ok=True)
    save_path = os.path.join(model_dir, "ball_predictor.pth")
    
    torch.save(model.state_dict(), save_path)
    print(f"📦 Model saved to {save_path}")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_ai_model()
