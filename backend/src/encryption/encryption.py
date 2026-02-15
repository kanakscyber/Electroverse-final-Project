import os
import json
import time
from datetime import datetime
from pathlib import Path
from Crypto.Cipher import AES


class VideoEncryptor:
    def __init__(
        self,
        raw_folder=os.environ.get("EV_CV_DIR"),
        out_folder=os.environ.get("EV_ENC_DIR"),
        key_path=os.environ.get("EV_KEY_PATH"),
        scan_interval=10
    ):
        self.raw_folder = Path(raw_folder)
        self.out_folder = Path(out_folder)
        self.key_path = Path(key_path)
        self.scan_interval = scan_interval
        
        self.out_folder.mkdir(parents=True, exist_ok=True)
        self.key = self.load_key()
    
    def load_key(self):
        """Load encryption key."""
        if not self.key_path.exists():
            raise FileNotFoundError(f"Encryption key not found: {self.key_path}")
        
        with open(self.key_path, 'rb') as f:
            return f.read()
    
    def wait_for_stable_file(self, filepath, wait_seconds=3):
        """Wait until file stops growing."""
        if not filepath.exists():
            return False
        
        size1 = filepath.stat().st_size
        time.sleep(wait_seconds)
        
        if not filepath.exists():
            return False
            
        size2 = filepath.stat().st_size
        return size1 == size2
    
    def encrypt_file(self, filepath):
        """Encrypt a single video file using AES-EAX."""
        try:
            # Read video data
            with open(filepath, 'rb') as f:
                plaintext = f.read()
            
            # Encrypt
            cipher = AES.new(self.key, AES.MODE_EAX)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            
            # Output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_name = f"enc_{timestamp}.WattLagGyi"
            output_path = self.out_folder / output_name
            
            # Write encrypted file: nonce + tag + ciphertext
            with open(output_path, 'wb') as f:
                f.write(cipher.nonce)  # 16 bytes
                f.write(tag)           # 16 bytes
                f.write(ciphertext)
            
            print(f"✓ Encrypted: {filepath.name} -> {output_name} ({len(ciphertext)} bytes)")
            
            # Delete original
            filepath.unlink()
            
            return output_path
            
        except Exception as e:
            print(f"✗ Encryption failed: {filepath.name} - {e}")
            return None
    
    def run(self):
        """Main encryption loop."""
        print(f"Video encryption started")
        print(f"Watching: {self.raw_folder}")
        print(f"Output: {self.out_folder}")
        print(f"Scan interval: {self.scan_interval}s")
        
        while True:
            try:
                # Find MP4 files
                files = sorted(self.raw_folder.glob("*.mp4"))
                
                for filepath in files:
                    # Wait for file to stabilize
                    if not self.wait_for_stable_file(filepath):
                        continue
                    
                    # Encrypt
                    self.encrypt_file(filepath)
                
            except Exception as e:
                print(f"Error in encryption loop: {e}")
            
            time.sleep(self.scan_interval)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Encrypt video files')
    parser.add_argument('--raw-folder', default=os.environ.get('EV_RAW_FOLDER', 'data/raw_buffer'), help='Raw video folder')
    parser.add_argument('--out-folder', default=os.environ.get('EV_OUT_FOLDER', 'data/encrypted'), help='Encrypted output folder')
    parser.add_argument('--key-path', default=os.environ.get('EV_KEY_PATH', 'configs/secret.key'), help='Encryption key path')
    parser.add_argument('--interval', type=int, default=10, help='Scan interval (seconds)')
    
    args = parser.parse_args()
    
    encryptor = VideoEncryptor(
        raw_folder=args.raw_folder,
        out_folder=args.out_folder,
        key_path=args.key_path,
        scan_interval=args.interval
    )
    
    encryptor.run()


if __name__ == '__main__':
    main()