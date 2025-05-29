# clean.py

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def delete_all_files():
    print("🧹 Deleting all files...")
    files = client.files.list().data
    for f in files:
        print(f"🗑️ Deleting file: {f.id} ({f.filename})")
        client.files.delete(f.id)
    print("✅ All files deleted.")

def delete_all_vector_stores():
    print("🧹 Deleting all vector stores...")
    vector_stores = client.vector_stores.list().data
    for store in vector_stores:
        print(f"🗑️ Deleting vector store: {store.id} ({store.name})")
        client.vector_stores.delete(store.id)
    print("✅ All vector stores deleted.")

if __name__ == "__main__":
    delete_all_files()
    delete_all_vector_stores()
    print("✅ Cleanup complete.")