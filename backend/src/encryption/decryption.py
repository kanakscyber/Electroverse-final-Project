import os
import tempfile
from pathlib import Path
from Crypto.Cipher import AES


def load_key(key_path=None):
    """Load decryption key."""
    if key_path is None:
        key_path = os.environ.get("EV_KEY_PATH") or "configs/secret.key"
    
    key_path = Path(key_path)
    if not key_path.exists():
        raise FileNotFoundError(f"Key not found: {key_path}")
    
    with open(key_path, 'rb') as f:
        return f.read()


def decrypt_blob_to_path(blob_bytes, key):
    """
    Decrypt a blob in simple format: nonce[16] + tag[16] + ciphertext
    Returns path to temporary .mp4 file or None on failure.
    """
    try:
        if len(blob_bytes) < 32:
            return None
        
        # Extract components
        nonce = blob_bytes[:16]
        tag = blob_bytes[16:32]
        ciphertext = blob_bytes[32:]
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        
        # Write to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.write(plaintext)
        tmp.flush()
        tmp.close()
        
        return tmp.name
        
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def decrypt_file(input_path, output_path, key):
    """Decrypt a file from disk."""
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()
    
    temp_path = decrypt_blob_to_path(encrypted_data, key)
    
    if temp_path:
        # Move to final location
        os.rename(temp_path, output_path)
        print(f"✓ Decrypted: {input_path} -> {output_path}")
        return True
    else:
        print(f"✗ Decryption failed: {input_path}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Decrypt video file')
    parser.add_argument('input', help='Encrypted input file')
    parser.add_argument('output', help='Decrypted output file')
    parser.add_argument('--key', default='configs/secret.key', help='Key file path')
    
    args = parser.parse_args()
    
    key = load_key(args.key)
    decrypt_file(args.input, args.output, key)


if __name__ == '__main__':
    main()