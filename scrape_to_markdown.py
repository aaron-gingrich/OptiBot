# scrape_to_markdown.py

import os
import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import hashlib
from urllib.parse import urlparse

# Base URL for API and article content
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUTPUT_DIR = "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def slugify(text):
    """
    Create a filename-safe slug from article title or URL.
    """
    text = text.lower().strip().replace(" ", "-").replace("/", "-")
    return re.sub(r'[^a-zA-Z0-9\-_]', '', text)  # Remove illegal filename characters

def get_articles():
    """
    Use the Zendesk API to get article metadata and body HTML.
    """
    print("🔍 Fetching articles via Zendesk API...")
    articles = []
    page = 1
    while True:
        print(f"🌐 Fetching page {page} from Zendesk API...")
        res = requests.get(API_URL, params={"page": page}, headers=HEADERS)
        if res.status_code != 200:
            print(f"❌ Failed to fetch page {page}: status {res.status_code}")
            break

        data = res.json()
        batch = data.get("articles", [])
        if not batch:
            print("🚫 No more articles found. Done.")
            break

        articles.extend(batch)

        if not data.get("next_page"):
            break

        page += 1

    print(f"✅ Retrieved {len(articles)} total articles.")
    return articles

def clean_article_html(html):
    """
    Clean up article HTML and convert to Markdown.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("nav, footer, .header, .breadcrumbs"):
        tag.decompose()
    return md(str(soup))

def download_and_convert():
    """
    Convert and save articles from the Zendesk API directly.
    """
    articles = get_articles()
    count = 0

    for article in articles:
        title = article.get("title", "untitled")
        html = article.get("body", "")
        if not html:
            print(f"⚠️ No body found for: {title}, skipping.")
            continue

        print(f"⬇️  Converting: {title}")
        md_content = clean_article_html(html)
        slug = slugify(title)[:50]  # limit filename length
        output_path = f"{OUTPUT_DIR}/{slug}.md"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"📝 Saved: {output_path}")
        except OSError as e:
            print(f"❌ Failed to save {slug}.md: {e}")
            continue

        count += 1
        if count >= 30:
            print("🚦 Reached 30 articles. Stopping.")
            break

    print(f"✅ Finished writing {count} Markdown files to ./{OUTPUT_DIR}")

if __name__ == "__main__":
    print("🚀 Starting scraper using Zendesk API (direct body)...")
    download_and_convert()
    print("🏁 Done!")
