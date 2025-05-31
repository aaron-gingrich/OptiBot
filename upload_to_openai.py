#!/usr/bin/env python3
""" 
upload_to_openai.py

Uploads Markdown files from the data/ directory to OpenAI’s vector store via API.
Skips unchanged files using SHA-256 content hashing, deletes older file versions, and logs the run.

This script is production-ready and includes:
- Delta detection based on content hash
- File upload via OpenAI API
- Auto-deletion of older file versions
- Attachment to a named vector store
- Summary logging per run

Requirements:
- requests
- python-dotenv
- A .env file with OPENAI_API_KEY

Usage:
    python upload_to_openai.py
"""

import os
import json
import hashlib
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# Constants
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "OpenAI-Beta": "assistants=v2"
}
BASE_URL = "https://api.openai.com/v1"
DATA_DIR = "data"
VECTOR_STORE_NAME = "optibot-vector-store"
UPLOAD_LOG_PATH = os.path.join(DATA_DIR, "upload_log.json")

def hash_content(content):
    """Return SHA-256 hash of file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def load_upload_log():
    """Load existing upload log from disk."""
    if os.path.exists(UPLOAD_LOG_PATH):
        with open(UPLOAD_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_upload_log(log):
    """Save updated upload log to disk."""
    with open(UPLOAD_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

def get_existing_files():
    """Fetch list of already uploaded files."""
    res = requests.get(f"{BASE_URL}/files", headers=HEADERS)
    res.raise_for_status()
    return {f["filename"]: f["id"] for f in res.json().get("data", [])}

def get_existing_vector_stores():
    """Fetch existing vector stores."""
    res = requests.get(f"{BASE_URL}/vector_stores", headers=HEADERS)
    res.raise_for_status()
    return {v["name"]: v["id"] for v in res.json().get("data", [])}

def create_or_get_vector_store():
    """Return existing vector store ID or create one."""
    stores = get_existing_vector_stores()
    if VECTOR_STORE_NAME in stores:
        print(f"Reusing existing vector store: {VECTOR_STORE_NAME}")
        return stores[VECTOR_STORE_NAME]

    res = requests.post(f"{BASE_URL}/vector_stores", headers=HEADERS, json={"name": VECTOR_STORE_NAME})
    res.raise_for_status()
    return res.json()["id"]

def attach_file_to_vector_store(vector_store_id, file_ids):
    """Attach uploaded files to the vector store in batches."""
    print(f"Attaching {len(file_ids)} files to vector store...")
    for i in range(0, len(file_ids), 50):
        batch = file_ids[i:i + 50]
        res = requests.post(
            f"{BASE_URL}/vector_stores/{vector_store_id}/file_batches",
            headers=HEADERS,
            json={"file_ids": batch}
        )
        res.raise_for_status()
        print(f"Attached batch {i // 50 + 1}: {len(batch)} files")

def delete_file(file_id):
    """Delete an old file from OpenAI."""
    try:
        res = requests.delete(f"{BASE_URL}/files/{file_id}", headers=HEADERS)
        res.raise_for_status()
        print(f"Deleted old file: {file_id}")
    except Exception as e:
        print(f"Failed to delete file {file_id}: {e}")

def upload_files_to_vector_store():
    """Main function: upload new/changed files and attach to vector store."""
    print("Uploading Markdown files to OpenAI...")

    run_started = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    upload_log = load_upload_log()
    existing_files = get_existing_files()

    file_ids = []
    added = updated = skipped = 0

    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".md"):
            continue

        path = os.path.join(DATA_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            content_hash = hash_content(content)

            prev = upload_log.get(fname)
            if prev and prev.get("hash") == content_hash:
                print(f"Skipping unchanged file: {fname}")
                skipped += 1
                continue
            elif prev:
                updated += 1
            else:
                added += 1

            # Upload new file
            with open(path, "rb") as f:
                res = requests.post(
                    f"{BASE_URL}/files",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    files={"file": (fname, f), "purpose": (None, "assistants")}
                )
                res.raise_for_status()
                file_id = res.json()["id"]
                print(f"Uploaded {fname} → {file_id}")
                file_ids.append(file_id)

                # Delete old version if applicable
                if prev and prev.get("file_id"):
                    delete_file(prev["file_id"])

                upload_log[fname] = {
                    "file_id": file_id,
                    "hash": content_hash,
                    "uploaded_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }

        except Exception as e:
            print(f"[ERROR] Failed to upload {fname}: {e}")

    save_upload_log(upload_log)

    if file_ids:
        vector_store_id = create_or_get_vector_store()
        attach_file_to_vector_store(vector_store_id, file_ids)
    else:
        print("No new or updated files to attach.")

    # Log summary
    run_ended = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "run_started": run_started,
            "run_ended": run_ended,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "attached_to_vector_store": bool(file_ids),
            "upload_log_path": UPLOAD_LOG_PATH
        }, f, indent=2)

    print(f"Run complete. Summary log saved to {log_file}")
    print(f"Added: {added}, Updated: {updated}, Skipped: {skipped}")

if __name__ == "__main__":
    upload_files_to_vector_store()
