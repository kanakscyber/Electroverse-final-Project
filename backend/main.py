# backend/main.py - REPLACE

import threading
import time
import os
from pathlib import Path
from src.encryption.keyGeneration import load_key

load_key()

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('EV_DATA_DIR', ROOT / 'data'))
RAW_DIR = DATA_DIR / 'raw_buffer'
ENCRYPTED_DIR = DATA_DIR / 'encrypted'
CAMERA_ID = os.environ.get('EV_CAMERA_ID', 'cam_01')


def record_thread(stop_event):
    from src.camera.record import ContinuousRecorder
    try:
        recorder = ContinuousRecorder(
            camera_id=int(os.environ.get('EV_CAMERA_ID_NUM', 0)),
            output_dir=str(RAW_DIR),
            segment_duration=int(os.environ.get('EV_SEGMENT_DURATION', 180))
        )
        recorder.record()
    except Exception as e:
        print(f'❌ record_thread: {e}')
        import traceback; traceback.print_exc()


def encryption_thread(stop_event):
    from src.encryption.encryption import VideoEncryptor
    try:
        # FIX: Provide key_path explicitly
        key_path = os.environ.get('EV_KEY_PATH') or str(ROOT / 'configs' / 'secret.key')
        encryptor = VideoEncryptor(
            raw_folder=str(RAW_DIR),
            out_folder=str(ENCRYPTED_DIR),
            key_path=key_path,
            scan_interval=int(os.environ.get('EV_ENC_POLL', 10))
        )
        encryptor.run()
    except Exception as e:
        print(f'❌ encryption_thread: {e}')
        import traceback; traceback.print_exc()


def uploader_thread(stop_event):
    from src.encryption.uploader import VideoUploader
    try:
        uploader = VideoUploader(
            watch_dir=str(ENCRYPTED_DIR),
            camera_id=CAMERA_ID,
            scan_interval=int(os.environ.get('EV_UPLOAD_POLL', 10))
        )
        uploader.run()
    except Exception as e:
        print(f'❌ uploader_thread: {e}')
        import traceback; traceback.print_exc()


def server_thread(stop_event):
    from src.server.server import create_app
    app = create_app()
    
    cert = os.environ.get('EV_SSL_CERT', 'localhost-cert.pem')
    key = os.environ.get('EV_SSL_KEY', 'localhost-key.pem')
    
    ssl_context = None
    if os.path.exists(cert) and os.path.exists(key):
        ssl_context = (cert, key)
        print("✅ HTTPS on port 5000")
    else:
        print("⚠️ HTTP on port 5000")
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,
        use_reloader=False,
        ssl_context=ssl_context
    )


def main():
    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / 'configs').mkdir(parents=True, exist_ok=True)
    
    stop_event = threading.Event()

    threads = [
        threading.Thread(target=record_thread, args=(stop_event,), daemon=True, name="Recording"),
        threading.Thread(target=encryption_thread, args=(stop_event,), daemon=True, name="Encryption"),
        threading.Thread(target=uploader_thread, args=(stop_event,), daemon=True, name="Upload"),
        threading.Thread(target=server_thread, args=(stop_event,), daemon=True, name="Server"),
    ]

    print("\n🚀 Electroverse\n")
    print(f"📁 {DATA_DIR}")
    print(f"📹 {CAMERA_ID}\n")

    for t in threads:
        t.start()
        print(f"✅ {t.name}")

    print("\n📊 Running. Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n🛑 Stopping...')
        stop_event.set()


if __name__ == '__main__':
    main()