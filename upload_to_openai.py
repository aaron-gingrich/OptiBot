# upload_to_openai.py (Raw HTTP API version)

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}
FOLDER_PATH = "data"
VECTOR_STORE_NAME = "optibot-vector-store"

# Extract metadata from filename

def extract_metadata_from_filename(filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    return {
        "title": base.replace("-", " ").title(),
        "source": f"https://support.optisigns.com/hc/en-us/articles/{base}"
    }

# Check existing files

def list_existing_files():
    res = requests.get("https://api.openai.com/v1/files", headers=HEADERS)
    res.raise_for_status()
    return {f['filename']: f['id'] for f in res.json().get('data', [])}

# Check existing vector stores

def list_vector_stores():
    res = requests.get("https://api.openai.com/v1/vector_stores", headers=HEADERS)
    res.raise_for_status()
    return res.json().get("data", [])

# Upload file to OpenAI

def upload_file(filepath):
    with open(filepath, "rb") as f:
        files = {
            "file": (os.path.basename(filepath), f),
            "purpose": (None, "assistants")
        }
        res = requests.post("https://api.openai.com/v1/files", headers=HEADERS, files=files)
        res.raise_for_status()
        return res.json()["id"]

# Create new vector store

def create_vector_store(name):
    res = requests.post("https://api.openai.com/v1/vector_stores", headers=HEADERS, json={"name": name})
    res.raise_for_status()
    return res.json()["id"]

# Attach file to vector store

def attach_file_to_vector_store(vector_store_id, file_ids):
    res = requests.post(
        f"https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches",
        headers=HEADERS,
        json={"file_ids": file_ids}
    )
    res.raise_for_status()

# Main upload process

def upload_files_to_vector_store():
    print("🚀 Starting raw API file upload...")

    existing_files = list_existing_files()
    print(f"📁 Found {len(existing_files)} existing OpenAI files")

    file_ids = []
    for fname in os.listdir(FOLDER_PATH):
        if not fname.endswith(".md"):
            continue

        filepath = os.path.join(FOLDER_PATH, fname)

        if fname in existing_files:
            print(f"⚠️ Skipping already uploaded: {fname}")
            file_ids.append(existing_files[fname])
            continue

        print(f"📤 Uploading: {fname}...")
        file_id = upload_file(filepath)
        file_ids.append(file_id)
        print(f"✅ Uploaded: {file_id}")
        time.sleep(1)

    # Check for existing vector store
    existing_stores = list_vector_stores()
    vector_store = next((v for v in existing_stores if v['name'] == VECTOR_STORE_NAME), None)

    if vector_store:
        vector_store_id = vector_store['id']
        print(f"📂 Using existing vector store: {VECTOR_STORE_NAME} ({vector_store_id})")
    else:
        vector_store_id = create_vector_store(VECTOR_STORE_NAME)
        print(f"🆕 Created vector store: {VECTOR_STORE_NAME} ({vector_store_id})")

    # Attach files
    print("🔗 Attaching files to vector store...")
    attach_file_to_vector_store(vector_store_id, file_ids)
    print(f"✅ Done. Attached {len(file_ids)} files to vector store: {vector_store_id}")


if __name__ == "__main__":
    upload_files_to_vector_store()
