# upload_to_openai.py

import os
import json
import hashlib
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "OpenAI-Beta": "assistants=v2"
}
BASE_URL = "https://api.openai.com/v1"
DATA_DIR = "data"
VECTOR_STORE_NAME = "optibot-vector-store"
UPLOAD_LOG_PATH = os.path.join(DATA_DIR, "upload_log.json")


def hash_content(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_upload_log():
    if os.path.exists(UPLOAD_LOG_PATH):
        with open(UPLOAD_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_upload_log(log):
    with open(UPLOAD_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def get_existing_files():
    res = requests.get(f"{BASE_URL}/files", headers=HEADERS)
    res.raise_for_status()
    return {f["filename"]: f["id"] for f in res.json().get("data", [])}


def get_existing_vector_stores():
    res = requests.get(f"{BASE_URL}/vector_stores", headers=HEADERS)
    res.raise_for_status()
    return {v["name"]: v["id"] for v in res.json().get("data", [])}


def create_or_get_vector_store():
    existing_stores = get_existing_vector_stores()
    if VECTOR_STORE_NAME in existing_stores:
        print(f"Reusing existing vector store: {VECTOR_STORE_NAME}")
        return existing_stores[VECTOR_STORE_NAME]
    payload = {"name": VECTOR_STORE_NAME}
    res = requests.post(f"{BASE_URL}/vector_stores", headers=HEADERS, json=payload)
    res.raise_for_status()
    return res.json()["id"]


def attach_file_to_vector_store(vector_store_id, file_ids):
    print(f"Attaching {len(file_ids)} files in batches...")
    batch_size = 50
    for i in range(0, len(file_ids), batch_size):
        batch = file_ids[i:i + batch_size]
        payload = {"file_ids": batch}
        res = requests.post(
            f"{BASE_URL}/vector_stores/{vector_store_id}/file_batches",
            headers=HEADERS,
            json=payload
        )
        res.raise_for_status()
        print(f"Attached batch {i // batch_size + 1}: {len(batch)} files")


def delete_file(file_id):
    try:
        res = requests.delete(f"{BASE_URL}/files/{file_id}", headers=HEADERS)
        res.raise_for_status()
        print(f"Deleted old file: {file_id}")
    except Exception as e:
        print(f"Failed to delete old file {file_id}: {e}")


def upload_files_to_vector_store():
    print("Starting raw API file upload...")

    now_utc = datetime.now(timezone.utc)
    run_started = now_utc.isoformat().replace('+00:00', 'Z')
    uploaded_files = get_existing_files()
    upload_log = load_upload_log()
    file_ids = []

    added, updated, skipped = 0, 0, 0

    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".md"):
            continue

        base_name = fname.replace(".md", "")
        md_path = os.path.join(DATA_DIR, fname)

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            current_hash = hash_content(content)

            prev_hash = upload_log.get(fname, {}).get("hash")
            if prev_hash:
                if prev_hash == current_hash:
                    print(f"Skipping unchanged file: {fname}")
                    skipped += 1
                    continue
                else:
                    updated += 1
            else:
                added += 1

            with open(md_path, "rb") as f:
                res = requests.post(
                    f"{BASE_URL}/files",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    files={"file": (fname, f), "purpose": (None, "assistants")}
                )
                res.raise_for_status()
                file_id = res.json()["id"]
                file_ids.append(file_id)

                print(f"Uploaded file: {fname} → {file_id}")

                old_file_id = upload_log.get(fname, {}).get("file_id")
                if old_file_id:
                    delete_file(old_file_id)

                upload_log[fname] = {
                    "file_id": file_id,
                    "hash": current_hash,
                    "uploaded_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }

        except Exception as e:
            print(f"❌ Failed to upload {fname}: {e}")

    save_upload_log(upload_log)

    if file_ids:
        vector_store_id = create_or_get_vector_store()
        attach_file_to_vector_store(vector_store_id, file_ids)
        print(f"All files attached to vector store: {vector_store_id}")
    else:
        print("No new or changed files to attach.")

    # Log run summary
    run_ended = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    os.makedirs("logs", exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join("logs", f"run_log_{timestamp_str}.json")

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_started": run_started,
            "run_ended": run_ended,
            "total_scanned": added + updated + skipped,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "attached_to_vector_store": bool(file_ids),
            "upload_log_path": UPLOAD_LOG_PATH
        }, f, indent=2)

    print(f"Run log saved to {log_path}")
    print("\nRun Summary:")
    print(f"   Added:   {added}")
    print(f"   Updated: {updated}")
    print(f"   Skipped: {skipped}")
    print(f"   Log file: {log_path}")


if __name__ == "__main__":
    upload_files_to_vector_store()
