import os
import subprocess
import sys

FILES = [
    ('1_Pooling/config.json', '1_Pooling/config.json'),
    ('config.json', 'config.json'),
    ('config_sentence_transformers.json', 'config_sentence_transformers.json'),
    ('model.safetensors', 'model.safetensors'),
    ('modules.json', 'modules.json'),
    ('sentence_bert_config.json', 'sentence_bert_config.json'),
    ('special_tokens_map.json', 'special_tokens_map.json'),
    ('tokenizer.json', 'tokenizer.json'),
    ('tokenizer_config.json', 'tokenizer_config.json'),
    ('vocab.txt', 'vocab.txt'),
]

BASE_URL = 'https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main'

def provision():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, 'model_cache', 'BAAI', 'bge-small-en-v1.5')
    os.makedirs(target_dir, exist_ok=True)
    print(f'Provisioning into: {target_dir}')

    for remote, local in FILES:
        dest_path = os.path.join(target_dir, local.replace('/', os.sep))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        # Check if already downloaded and valid (> 1000 bytes for safetensors, > 50 for json)
        min_size = 100000000 if 'safetensors' in local else 50
        if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_size:
            print(f'Already exists: {local} ({os.path.getsize(dest_path)} bytes)')
            continue
        
        url = f'{BASE_URL}/{remote}'
        print(f'Downloading {local} via curl -6 from {url} ...')
        cmd = ['curl.exe', '-6', '-L', '-f', '-s', '-S', '--connect-timeout', '15', '-o', dest_path, url]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f'ERROR downloading {local}: {res.stderr}')
            sys.exit(1)
        print(f'Downloaded {local}: {os.path.getsize(dest_path)} bytes')

    print('SUCCESS: All BAAI/bge-small-en-v1.5 files provisioned locally!')

if __name__ == '__main__':
    provision()
