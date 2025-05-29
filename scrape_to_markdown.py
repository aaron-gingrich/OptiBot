# scrape_to_markdown.py

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import hashlib
from urllib.parse import urlparse

# Base URL for API and article content (sorted by most recently updated)
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUTPUT_DIR = "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_ARTICLES = 5  # Number of articles to process

def slugify(text):
    """
    Create a filename-safe slug from article title or URL.
    """
    text = text.lower().strip().replace(" ", "-").replace("/", "-")
    return re.sub(r'[^a-zA-Z0-9\-_]', '', text)  # Remove illegal filename characters

def get_articles(max_articles=MAX_ARTICLES):
    """
    Use the Zendesk API to get the most recently updated article metadata and body HTML.
    Only fetch as many articles as needed.
    """
    print("🔍 Fetching most recently updated articles via Zendesk API...")
    articles = []
    page = 1
    per_page = max_articles  # Fetch just enough on page 1 if possible

    params = {
        "page": page,
        "per_page": per_page,
        "sort_by": "updated_at",
        "sort_order": "desc"
    }

    res = requests.get(API_URL, params=params, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Failed to fetch articles: status {res.status_code}")
        return []

    data = res.json()

    # Save the full JSON response
    with open("api_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        print("💾 Saved full API response to api_response.json")

    articles = data.get("articles", [])
    print(f"✅ Retrieved {len(articles)} articles.")
    return articles[:max_articles]

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
        md_output_path = f"{OUTPUT_DIR}/{slug}.md"
        json_output_path = f"{OUTPUT_DIR}/{slug}.json"

        try:
            with open(md_output_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"📝 Saved Markdown: {md_output_path}")

            metadata = {
                "id": article.get("id"),
                "title": article.get("title"),
                "html_url": article.get("html_url"),
                "label_names": article.get("label_names", []),
                "created_at": article.get("created_at"),
                "updated_at": article.get("updated_at"),
                "section_id": article.get("section_id"),
                "content_tag_ids": article.get("content_tag_ids", [])
            }

            with open(json_output_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            print(f"📎 Saved Metadata: {json_output_path}")

        except OSError as e:
            print(f"❌ Failed to save files for {slug}: {e}")
            continue

        count += 1
        if count >= MAX_ARTICLES:
            print("🚦 Reached article limit. Stopping.")
            break

    print(f"✅ Finished writing {count} Markdown and JSON files to ./{OUTPUT_DIR}")

if __name__ == "__main__":
    print("🚀 Starting scraper using Zendesk API (most recent articles)...")
    download_and_convert()
    print("🏁 Done!")
