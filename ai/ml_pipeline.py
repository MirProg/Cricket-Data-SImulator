import sqlite3
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import logging
import os
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ML_PIPELINE - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricket_db.sqlite'

class CricketDatabaseDataset(Dataset):
    """
    Advanced PyTorch Dataset that streams from SQLite and extracts sequence features.
    """
    def __init__(self, db_path, sequence_length=22): # 11 players per team = 22 sequence length
        self.db_path = db_path
        self.sequence_length = sequence_length
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM CrawlQueue WHERE status='SUCCESS'")
            self.total_matches = min(cursor.fetchone()[0], 100000) # Limit to 100k for demonstration
        except sqlite3.OperationalError:
            self.total_matches = 1000
            
        conn.close()
        logger.info(f"Advanced Dataset initialized with {self.total_matches} records.")

    def __len__(self):
        return self.total_matches

    def __getitem__(self, idx):
        # In a real scenario, this would query the DB for the specific match idx.
        # We simulate fetching a sequence of 22 players (11 per team), each with 15 features
        # (e.g., batting average, bowling strike rate, age, recent form).
        
        # Sequence shape: (Sequence Length, Feature Dimension) = (22, 15)
        player_sequence = torch.randn(self.sequence_length, 15)
        
        # Target 1: Match Outcome (0 or 1)
        match_outcome = torch.randint(0, 2, (1,)).float()
        
        # Target 2: Top Batsman Runs (simulate a regression target 0-150 runs, normalized)
        top_batsman_runs = torch.rand(1) * 1.5 
        
        return player_sequence, match_outcome, top_batsman_runs

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=50):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x shape: (batch_size, seq_len, d_model)
        seq_len = x.size(1)
        x = x + self.pe[:seq_len, :].unsqueeze(0)
        return x

class AdvancedMatchPredictor(nn.Module):
    """
    A Transformer-based neural network for predicting match outcomes and player performance.
    """
    def __init__(self, feature_dim=15, d_model=64, nhead=4, num_layers=2, dim_feedforward=128, dropout=0.1):
        super(AdvancedMatchPredictor, self).__init__()
        
        # Input Embedding layer to project features to d_model
        self.embedding = nn.Linear(feature_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        # Transformer Encoder
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, 
            dropout=dropout, batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers=num_layers)
        
        # Output Heads
        # Head 1: Predict match outcome (binary classification)
        self.outcome_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Head 2: Predict top batsman runs (regression)
        self.runs_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, src):
        # src shape: (batch_size, seq_len, feature_dim)
        x = self.embedding(src)
        x = self.pos_encoder(x)
        
        # Pass through transformer
        transformer_out = self.transformer_encoder(x)
        
        # Global Average Pooling across the sequence dimension
        pooled = transformer_out.mean(dim=1)
        
        # Multi-task outputs
        match_outcome = self.outcome_head(pooled)
        predicted_runs = self.runs_head(pooled)
        
        return match_outcome, predicted_runs

def train_model(epochs=3, batch_size=128, lr=0.0005):
    logger.info("Initializing Advanced Transformer Training Pipeline...")
    
    dataset = CricketDatabaseDataset(DB_PATH)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on device: {device}")
    
    model = AdvancedMatchPredictor().to(device)
    
    # Loss functions for Multi-Task learning
    criterion_classification = nn.BCELoss() # For match outcome
    criterion_regression = nn.MSELoss()     # For player runs
    
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    
    model.train()
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        
        for batch_idx, (sequences, outcomes, runs) in enumerate(dataloader):
            sequences = sequences.to(device)
            outcomes = outcomes.to(device)
            runs = runs.to(device)
            
            optimizer.zero_grad()
            
            # Forward pass
            pred_outcomes, pred_runs = model(sequences)
            
            # Calculate composite loss
            loss_c = criterion_classification(pred_outcomes, outcomes)
            loss_r = criterion_regression(pred_runs, runs)
            total_loss = loss_c + (0.1 * loss_r) # Weight regression lower
            
            total_loss.backward()
            
            # Gradient clipping to prevent exploding gradients in transformers
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            epoch_loss += total_loss.item()
            
            # Simulate only 5 batches for demonstration
            if batch_idx >= 4:
                break
                
        logger.info(f"Epoch [{epoch+1}/{epochs}] - Multi-Task Loss: {epoch_loss/5:.4f}")
        
    os.makedirs('models', exist_ok=True)
    torch.save(model.state_dict(), 'models/advanced_predictor.pth')
    logger.info("Transformer Model saved to models/advanced_predictor.pth")

if __name__ == "__main__":
    train_model()
