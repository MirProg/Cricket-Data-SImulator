import time
import os
import subprocess
import logging
import schedule

logging.basicConfig(level=logging.INFO, format='%(asctime)s - CLAUDE-AUTO - %(levelname)s - %(message)s')

def run_distributed_scrapers():
    logging.info("Starting Distributed Historical Load Balancer...")
    subprocess.run(["python", "data/load_balancer.py"], check=False)
    logging.info("Distributed scrape chunk complete.")

def retrain_ai():
    logging.info("Starting advanced PyTorch AI retraining with latest data...")
    subprocess.run(["python", "cricket_simulator.py", "ai-train"], check=True)
    logging.info("AI Model updated.")

def push_to_github():
    logging.info("Pushing latest database and AI weights to GitHub...")
    subprocess.run(["git", "add", "."], check=True)
    # Using a generic message for automated commits
    subprocess.run(["git", "commit", "-m", "Auto-update: Database and AI weights sync"], check=False)
    subprocess.run(["git", "push"], check=True)
    logging.info("GitHub sync complete.")

def poll_live_matches():
    # This keeps the live tracker hot
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/api/live")
        logging.info("Polled live matches from FastAPI backend.")
    except Exception as e:
        logging.warning(f"FastAPI backend might not be running: {e}")

def run_daemon():
    logging.info("🏏 Claude AI Cricket Simulator Automation Daemon Started 🏏")
    
    # Schedule massive updates (e.g., weekly or daily)
    schedule.every().day.at("02:00").do(run_distributed_scrapers)
    schedule.every().day.at("03:00").do(retrain_ai)
    schedule.every().day.at("04:00").do(push_to_github)
    
    # Schedule live match polling (every 5 minutes)
    schedule.every(5).minutes.do(poll_live_matches)
    
    # Run loop
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # If run with --now, execute immediately before entering loop
    import sys
    if "--now" in sys.argv:
        run_distributed_scrapers()
        retrain_ai()
        push_to_github()
    run_daemon()
