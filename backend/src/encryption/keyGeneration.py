# src/encryption/keyGeneration.py - REPLACE

import os
from pathlib import Path
from Crypto.Random import get_random_bytes

# Get base dir (backend/)
BASE_DIR = Path(__file__).resolve().parents[2]  # Go up 2 levels from src/encryption/
CONFIG_DIR = BASE_DIR / "configs"
KEY_PATH = CONFIG_DIR / "secret.key"

def load_key():
    if not KEY_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        key = get_random_bytes(32)
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        print(f"✅ Generated new key: {KEY_PATH}")
        return key

    with open(KEY_PATH, "rb") as f:
        return f.read()