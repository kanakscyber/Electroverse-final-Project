import os
import json
import time
from datetime import datetime
from Crypto.Cipher import AES

RAW_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\raw_buffer"
OUT_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\encrypted"
KEY_PATH = r"E:\Clubs and other things\electroverse\encryption\configs\secret.key"
LOG_PATH = r"E:\Clubs and other things\electroverse\encryption\configs\processed_log.json"

SCAN_INTERVAL = 10


def load_key():
    with open(KEY_PATH, "rb") as f:
        return f.read()


def load_log():
    if not os.path.exists(LOG_PATH):
        return {}

    with open(LOG_PATH, "r") as f:
        return json.load(f)


def save_log(log):
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def generate_time_markers(duration_minutes):
    markers = []

    for m in range(0, duration_minutes + 1, 3):
        hh = m // 60
        mm = m % 60
        markers.append(f"{hh:02}:{mm:02}")

    return markers


def encrypt_chunk(file_path, key):
    with open(file_path, "rb") as f:
        data = f.read()

    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)

    file_size = os.path.getsize(file_path)
    duration_minutes = max(1, file_size // (1024 * 1024))
    markers = generate_time_markers(duration_minutes)

    chunk_header = {
        "filename": os.path.basename(file_path),
        "timestamp": str(datetime.now()),
        "file_size": file_size,
        "duration_est_min": duration_minutes,
        "markers_3min": markers
    }

    header_bytes = json.dumps(chunk_header).encode()
    header_len = len(header_bytes).to_bytes(4, "big")

    return header_len + header_bytes + cipher.nonce + tag + ciphertext


def get_daily_container():
    today = datetime.now().strftime("%Y-%m-%d")
    output_name = f"{today}.WattLagGyi"
    output_path = os.path.join(OUT_FOLDER, output_name)

    if not os.path.exists(output_path):
        day_header = {
            "date": today,
            "camera_id": "CAM_67",
            "encryption": "AES-256-EAX",
            "created_at": str(datetime.now())
        }

        header_bytes = json.dumps(day_header).encode()
        header_len = len(header_bytes).to_bytes(4, "big")

        with open(output_path, "wb") as f:
            f.write(header_len)
            f.write(header_bytes)

        print(f"Created new daily container → {output_name}")

    return output_path, today


def live_encrypt():
    key = load_key()
    log = load_log()

    print("Live encryption started...\n")

    while True:
        output_path, today = get_daily_container()

        if today not in log:
            log[today] = []

        files = [
            f for f in os.listdir(RAW_FOLDER)
            if f.endswith(".mp4")
        ]

        for file in files:
            if file in log[today]:
                continue

            full_path = os.path.join(RAW_FOLDER, file)

            try:
                chunk_blob = encrypt_chunk(full_path, key)

                with open(output_path, "ab") as out:
                    out.write(chunk_blob)

                log[today].append(file)
                save_log(log)

                os.remove(full_path)

                print(f"Encrypted, appended & deleted → {file}")

            except Exception as e:
                print(f"Error processing {file}: {e}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    live_encrypt()
