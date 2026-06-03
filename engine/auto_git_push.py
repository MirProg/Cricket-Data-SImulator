import os
import time
import subprocess
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

REPO_DIR = r"C:\Users\seo\.local\bin\cricket_simulator"
INTERVAL_SECONDS = 1800  # 30 minutes

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, cwd=REPO_DIR, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def auto_push():
    logging.info("Starting Auto Git Updater (Interval: 30 minutes)")
    while True:
        time.sleep(INTERVAL_SECONDS)
        
        # Check if there are changes
        success, status = run_cmd("git status --porcelain")
        if not success or not status.strip():
            logging.info("No changes to commit. Sleeping...")
            continue
            
        logging.info("Changes detected. Committing and pushing...")
        run_cmd("git add -A")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_cmd(f'git commit -m "Auto-backup during massive scrape: {timestamp}"')
        
        success, out = run_cmd("git push origin main")
        if success:
            logging.info(f"Successfully pushed at {timestamp}")
        else:
            logging.error(f"Failed to push: {out}")

if __name__ == "__main__":
    auto_push()
