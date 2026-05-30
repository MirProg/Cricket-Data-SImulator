import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from .predictor import DeepCricketTransformer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)

class AdvancedCricketDataset(Dataset):
    def __init__(self, num_samples=300000):
        self.num_samples = num_samples
        self.features = []
        self.labels = []
        self._generate_synthetic_data()

    def _generate_synthetic_data(self):
        logger.info(f"Generating {self.num_samples} advanced synthetic sequence samples with scorecard context...")
        
        # 12 context features
        bat_avg = np.random.uniform(5.0, 60.0, self.num_samples)
        bat_sr = np.random.uniform(50.0, 200.0, self.num_samples)
        bat_form = np.random.uniform(0.5, 1.5, self.num_samples)
        bowl_avg = np.random.uniform(15.0, 50.0, self.num_samples)
        bowl_econ = np.random.uniform(3.5, 12.0, self.num_samples)
        bowl_form = np.random.uniform(0.5, 1.5, self.num_samples)
        fmt = np.random.choice([0.0, 0.5, 1.0], self.num_samples)
        pitch = np.random.uniform(0.7, 1.3, self.num_samples)
        
        # Scorecard context
        score = np.random.uniform(0, 300, self.num_samples)
        wickets = np.random.uniform(0, 9, self.num_samples)
        overs = np.random.uniform(0, 50, self.num_samples)
        target = np.random.uniform(0, 350, self.num_samples)

        # Normalize features
        self.features = np.column_stack([
            bat_avg / 50.0,
            bat_sr / 150.0,
            bat_form,
            bowl_avg / 40.0,
            bowl_econ / 10.0,
            bowl_form,
            fmt,
            pitch,
            score / 300.0,
            wickets / 10.0,
            overs / 50.0,
            target / 300.0
        ])
        
        # The transformer expects seq_len. We will reshape this in __getitem__ to (1, 12)
        
        # Target Generation using heuristics (mimicking real cricket physics)
        for i in range(self.num_samples):
            b_avg = bat_avg[i]
            b_sr = bat_sr[i]
            bw_avg = bowl_avg[i]
            bw_ec = bowl_econ[i]
            
            # Wicket probability
            w_prob = (40.0 / bw_avg) * (15.0 / b_avg) * pitch[i]
            w_prob = np.clip(w_prob * 0.05, 0.01, 0.20)
            
            # Boundary probability
            bound_prob = (b_sr / 100.0) * (10.0 / bw_ec) * (1.0 / pitch[i])
            bound_prob = np.clip(bound_prob * 0.15, 0.05, 0.40)
            
            probs = np.array([
                w_prob,                      # 0 Wicket
                0.35,                        # 1 Dot
                0.30,                        # 2 Run 1
                0.08,                        # 3 Run 2
                0.02,                        # 4 Run 3
                bound_prob * 0.7,            # 5 Run 4
                bound_prob * 0.3             # 6 Six
            ])
            
            # Additional context adjustments:
            # If chasing a high target late in the innings, boundaries & wickets increase
            if target[i] > 0 and (target[i] - score[i] > 50) and overs[i] > 15:
                probs[0] *= 1.5 # high risk wicket
                probs[5] *= 1.3 # high risk 4
                probs[6] *= 1.5 # high risk 6
                
            probs /= probs.sum()
            label = np.random.choice(7, p=probs)
            self.labels.append(label)

        self.labels = np.array(self.labels)

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        # Return as sequence (seq_len=1, features=12)
        return torch.FloatTensor([self.features[idx]]), torch.LongTensor([self.labels[idx]])[0]

def train_advanced_model(epochs=5, batch_size=256):
    os.makedirs(os.path.join(os.path.dirname(__file__), 'models'), exist_ok=True)
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'advanced_predictor.pth')
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = DeepCricketTransformer().to(device)
    
    dataset = AdvancedCricketDataset()
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=2)
    
    logger.info(f"Starting advanced Transformer training on {device} for {epochs} epochs...")
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        
        for batch_features, batch_labels in dataloader:
            batch_features, batch_labels = batch_features.to(device), batch_labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            correct += (predicted == batch_labels).sum().item()
            
        avg_loss = total_loss / len(dataloader)
        accuracy = 100 * correct / dataset.num_samples
        scheduler.step(avg_loss)
        
        logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f} - Accuracy: {accuracy:.2f}%")
        
    torch.save(model.state_dict(), model_path)
    logger.info(f"Advanced model saved to {model_path}")
    return model_path

if __name__ == "__main__":
    train_advanced_model()
