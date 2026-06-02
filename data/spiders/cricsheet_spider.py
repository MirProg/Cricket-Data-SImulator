import os
import requests
import zipfile
import io

URL = "https://cricsheet.org/downloads/all_json.zip"
RAW_DIR = "data/raw/cricsheet"

def download_and_extract():
    os.makedirs(RAW_DIR, exist_ok=True)
    
    print(f"[*] Downloading T20 International JSON archive from {URL}...")
    headers = {
        "User-Agent": "CricMatrix Research Spider v1.0 (contact@cricmatrix.ai)"
    }
    
    # Send request
    response = requests.get(URL, headers=headers, stream=True)
    
    if response.status_code == 200:
        print("[+] Download complete. Extracting files to Bronze Layer...")
        # Read the zip file from memory
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(RAW_DIR)
        
        # Count files
        num_files = len([f for f in os.listdir(RAW_DIR) if f.endswith(".json")])
        print(f"[+] Successfully extracted {num_files} JSON files to {RAW_DIR}")
    else:
        print(f"[!] Failed to download. Status code: {response.status_code}")

if __name__ == "__main__":
    download_and_extract()
