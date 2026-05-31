import optuna
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import logging
from ml_pipeline import AdvancedMatchPredictor, CricketDatabaseDataset, DB_PATH

logging.basicConfig(level=logging.INFO, format='%(asctime)s - TUNE_MODEL - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def objective(trial):
    # Hyperparameters to tune
    d_model = trial.suggest_categorical('d_model', [32, 64, 128])
    nhead = trial.suggest_categorical('nhead', [2, 4, 8])
    num_layers = trial.suggest_int('num_layers', 1, 3)
    lr = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
    dropout = trial.suggest_float('dropout', 0.1, 0.5)
    
    # Initialize Data
    dataset = CricketDatabaseDataset(DB_PATH)
    dataloader = DataLoader(dataset, batch_size=128, shuffle=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Initialize Model with suggested parameters
    model = AdvancedMatchPredictor(
        feature_dim=15, 
        d_model=d_model, 
        nhead=nhead, 
        num_layers=num_layers,
        dropout=dropout
    ).to(device)
    
    criterion_c = nn.BCELoss()
    criterion_r = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr)
    
    model.train()
    
    # Train for 1 epoch just to get a validation score for tuning speed
    epoch_loss = 0.0
    for batch_idx, (sequences, outcomes, runs) in enumerate(dataloader):
        sequences, outcomes, runs = sequences.to(device), outcomes.to(device), runs.to(device)
        
        optimizer.zero_grad()
        pred_outcomes, pred_runs = model(sequences)
        
        loss = criterion_c(pred_outcomes, outcomes) + (0.1 * criterion_r(pred_runs, runs))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        epoch_loss += loss.item()
        
        if batch_idx >= 5: # Only 5 batches per trial for fast demonstration
            break
            
    # Return average loss for this trial (Optuna minimizes this)
    return epoch_loss / 5.0

def run_tuning():
    logger.info("Starting Hyperparameter Tuning with Optuna...")
    study = optuna.create_study(direction='minimize')
    
    # Run 5 trials
    study.optimize(objective, n_trials=5)
    
    logger.info("Tuning Complete!")
    logger.info("Best Trial Parameters:")
    for key, value in study.best_trial.params.items():
        logger.info(f"    {key}: {value}")
    logger.info(f"Best Loss: {study.best_value:.4f}")

if __name__ == "__main__":
    run_tuning()
