import subprocess
import sys

def run_scraper():
    print("=== Running Scraper ===")
    result = subprocess.run([sys.executable, "scrape_to_markdown.py"])
    if result.returncode != 0:
        print("Scraper failed.")
        sys.exit(result.returncode)

def run_uploader():
    print("=== Running Uploader ===")
    result = subprocess.run([sys.executable, "upload_to_openai.py"])
    if result.returncode != 0:
        print("Uploader failed.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    print(">>> Starting OptiBot Daily Job <<<")
    run_scraper()
    run_uploader()
    print(">>> Job Complete <<<")
