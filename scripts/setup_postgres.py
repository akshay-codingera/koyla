import os
import sys
import urllib.request
import zipfile
import shutil
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG_DIR = os.path.join(BASE_DIR, "pgsql")
DATA_DIR = os.path.join(PG_DIR, "data")
BIN_DIR = os.path.join(PG_DIR, "bin")

PG_URL = "https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64-binaries.zip"
PG_ZIP = os.path.join(BASE_DIR, "postgres16.zip")

VECTOR_URL = "https://github.com/andreiramani/pgvector_pgsql_windows/releases/download/0.8.6_16/vector.v0.8.6-pg16.zip"
VECTOR_ZIP = os.path.join(BASE_DIR, "vector.zip")

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        print(f"File already exists: {target_path} ({os.path.getsize(target_path)} bytes)")
        return
    print(f"Downloading {url} to {target_path} ...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
        total_size = int(response.info().get('Content-Length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = downloaded * 100 // total_size
                print(f"Progress: {percent}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end="\r")
        print("\nDownload complete.")

def main():
    print(f"Base Directory: {BASE_DIR}")
    
    # 1. Download PostgreSQL 16
    download_file(PG_URL, PG_ZIP)
    
    # 2. Extract PostgreSQL
    if not os.path.exists(BIN_DIR):
        print(f"Extracting PostgreSQL binaries to {BASE_DIR}...")
        with zipfile.ZipFile(PG_ZIP, 'r') as zip_ref:
            zip_ref.extractall(BASE_DIR)
        print("PostgreSQL extraction complete.")
    else:
        print(f"PostgreSQL already extracted at {PG_DIR}")
        
    # 3. Download pgvector
    download_file(VECTOR_URL, VECTOR_ZIP)
    
    # 4. Extract pgvector and copy to pgsql
    print("Installing pgvector extension...")
    temp_vector = os.path.join(BASE_DIR, "temp_vector")
    os.makedirs(temp_vector, exist_ok=True)
    with zipfile.ZipFile(VECTOR_ZIP, 'r') as zip_ref:
        zip_ref.extractall(temp_vector)
        
    # Copy files
    lib_dir = os.path.join(PG_DIR, "lib")
    ext_dir = os.path.join(PG_DIR, "share", "extension")
    
    for root, dirs, files in os.walk(temp_vector):
        for file in files:
            full_path = os.path.join(root, file)
            if file.endswith(".dll"):
                shutil.copy2(full_path, os.path.join(lib_dir, file))
                print(f"Copied {file} to {lib_dir}")
            elif file.endswith(".control") or file.endswith(".sql"):
                shutil.copy2(full_path, os.path.join(ext_dir, file))
                print(f"Copied {file} to {ext_dir}")
                
    shutil.rmtree(temp_vector, ignore_errors=True)
    print("pgvector installed into PostgreSQL extension directories.")
    
    # 5. Initialize cluster if data dir doesn't exist
    initdb_exe = os.path.join(BIN_DIR, "initdb.exe")
    if not os.path.exists(DATA_DIR):
        print(f"Initializing database cluster in {DATA_DIR}...")
        cmd = [initdb_exe, "-D", DATA_DIR, "-U", "postgres", "-A", "trust", "-E", "utf8"]
        subprocess.run(cmd, check=True)
        print("Database cluster initialized.")
    else:
        print(f"Data directory already exists at {DATA_DIR}")
        
    # 6. Start PostgreSQL service
    pg_ctl_exe = os.path.join(BIN_DIR, "pg_ctl.exe")
    logfile = os.path.join(PG_DIR, "server.log")
    print("Starting PostgreSQL server...")
    subprocess.run([pg_ctl_exe, "-D", DATA_DIR, "-l", logfile, "start"], check=True)
    
    # Wait for startup
    time.sleep(3)
    
    # 7. Create database koyla
    psql_exe = os.path.join(BIN_DIR, "psql.exe")
    print("Creating database 'koyla'...")
    res = subprocess.run([psql_exe, "-U", "postgres", "-c", "CREATE DATABASE koyla;"], capture_output=True, text=True)
    print(res.stdout, res.stderr)
    
    # 8. Enable pgvector
    print("Enabling pgvector extension in 'koyla'...")
    res = subprocess.run([psql_exe, "-U", "postgres", "-d", "koyla", "-c", "CREATE EXTENSION IF NOT EXISTS vector;"], capture_output=True, text=True)
    print(res.stdout, res.stderr)
    
    # 9. Verify pgvector
    print("Verifying pgvector extension in 'koyla'...")
    res = subprocess.run([psql_exe, "-U", "postgres", "-d", "koyla", "-c", "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"], capture_output=True, text=True)
    print(res.stdout)
    
    print("PostgreSQL + pgvector setup successfully completed!")

if __name__ == "__main__":
    main()
