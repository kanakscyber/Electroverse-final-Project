import os
import json
from Crypto.Cipher import AES

ENC_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\encrypted"
OUTPUT_FOLDER = r"E:\Clubs and other things\electroverse\encryption\data\decrypted"
KEY_PATH = r"E:\Clubs and other things\electroverse\encryption\configs\secret.key"


def load_key():
    with open(KEY_PATH, "rb") as f:
        return f.read()


def read_exact(f, size):
    data = b""
    while len(data) < size:
        chunk = f.read(size - len(data))
        if not chunk:
            raise EOFError
        data += chunk
    return data


def unique_output_path(name):
    base, ext = os.path.splitext(name)
    counter = 1
    path = os.path.join(OUTPUT_FOLDER, name)

    while os.path.exists(path):
        path = os.path.join(
            OUTPUT_FOLDER,
            f"{base}_{counter}{ext}"
        )
        counter += 1

    return path


def decrypt_container(container_path, key):

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(container_path, "rb") as f:

        day_header_len = int.from_bytes(read_exact(f, 4), "big")
        day_header = json.loads(read_exact(f, day_header_len).decode())

        print(f"\nProcessing → {os.path.basename(container_path)}")
        print("Header:", day_header)

        chunk_count = 0

        while True:
            try:
                header_len_bytes = f.read(4)

                if not header_len_bytes:
                    break

                chunk_header_len = int.from_bytes(header_len_bytes, "big")
                chunk_header = json.loads(
                    read_exact(f, chunk_header_len).decode()
                )

                nonce = read_exact(f, 16)
                tag = read_exact(f, 16)

                file_size = chunk_header["file_size"]
                ciphertext = read_exact(f, file_size)

                cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)

                output_name = chunk_header["filename"]
                output_path = unique_output_path(output_name)

                with open(output_path, "wb") as out:
                    out.write(plaintext)

                chunk_count += 1
                print(f"Decrypted → {os.path.basename(output_path)}")

            except EOFError:
                print("Reached end of container.")
                break

            except Exception as e:
                print("Stopped at corrupted/incomplete chunk:", e)
                break

        print(f"Total chunks decrypted: {chunk_count}")


def process_all_containers():

    key = load_key()

    files = [
        f for f in os.listdir(ENC_FOLDER)
        if f.endswith(".WattLagGyi")
    ]

    if not files:
        print("No containers found.")
        return

    for file in files:
        container_path = os.path.join(ENC_FOLDER, file)
        decrypt_container(container_path, key)


if __name__ == "__main__":
    process_all_containers()
