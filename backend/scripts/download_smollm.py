import os
import sys
import time
import urllib.request

FILES = [
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "model.safetensors"
]

BASE_URL = "https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/resolve/main"
TARGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache", "SmolLM2-135M-Instruct")

def download():
    os.makedirs(TARGET_DIR, exist_ok=True)
    print(f"Target directory: {TARGET_DIR}")

    for filename in FILES:
        target_path = os.path.join(TARGET_DIR, filename)
        url = f"{BASE_URL}/{filename}"

        # If already downloaded and has content
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            if filename != "model.safetensors" or os.path.getsize(target_path) > 250 * 1024 * 1024:
                print(f"[EXISTS] {filename} ({os.path.getsize(target_path)} bytes)")
                continue

        print(f"[DOWNLOADING] {filename} from {url}...")
        start_t = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "KOYLA-Downloader/1.0"})

        with urllib.request.urlopen(req, timeout=60.0) as resp, open(target_path, "wb") as f:
            total_len = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            last_print = 0
            chunk_size = 1024 * 1024 # 1MB

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if downloaded - last_print >= 10 * 1024 * 1024 or downloaded == total_len:
                    pct = (downloaded / total_len * 100) if total_len else 0
                    mb = downloaded / (1024 * 1024)
                    tot_mb = total_len / (1024 * 1024)
                    print(f"  {filename}: {mb:.1f}MB / {tot_mb:.1f}MB ({pct:.1f}%)")
                    last_print = downloaded

        dur = time.time() - start_t
        print(f"[DONE] {filename} ({os.path.getsize(target_path)} bytes) in {dur:.1f}s")

    print("\nAll model files downloaded successfully!")

if __name__ == "__main__":
    download()
