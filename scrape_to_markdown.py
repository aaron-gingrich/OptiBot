#!/usr/bin/env python3
""" 
scrape_to_markdown.py

Fetches articles from the OptiSigns Zendesk Help Center, converts them to Markdown with frontmatter metadata,
and saves both Markdown and JSON metadata files locally.

This script is production-ready and includes:
- Pagination through the Zendesk API
- HTML sanitization
- SHA-256 content hashing for change detection
- Structured frontmatter for downstream consumption

Requirements:
- requests
- beautifulsoup4
- markdownify

Usage:
    python scrape_to_markdown.py
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import hashlib

# ------------------------- Constants -------------------------

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUTPUT_DIR = "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------- Utility Functions -------------------------

def slugify(text):
    """Create a filename-safe slug from an article title or URL."""
    text = text.lower().strip().replace(" ", "-").replace("/", "-")
    return re.sub(r'[^a-zA-Z0-9\-_]', '', text)

def hash_content(content):
    """Return a SHA-256 hash of the given string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def get_articles():
    """Fetch all articles using Zendesk API with pagination."""
    print("Fetching articles via Zendesk API with pagination...")
    articles = []
    next_page = API_URL

    while next_page:
        res = requests.get(next_page, headers=HEADERS)
        if res.status_code != 200:
            print(f"[ERROR] Failed to fetch: {next_page} (Status {res.status_code})")
            break

        data = res.json()
        page_articles = data.get("articles", [])
        articles.extend(page_articles)
        next_page = data.get("next_page")

        print(f"Fetched {len(page_articles)} articles (Total so far: {len(articles)})")

    return articles

def clean_article_html(html):
    """Clean HTML by removing unwanted elements, then convert to Markdown."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("nav, footer, .header, .breadcrumbs"):
        tag.decompose()
    return md(str(soup))

# ------------------------- Main Conversion Logic -------------------------

def download_and_convert():
    """Download, convert, and save articles as Markdown and JSON files."""
    articles = get_articles()
    count = 0

    for article in articles:
        title = article.get("title", "untitled")
        html = article.get("body", "")
        if not html:
            print(f"[WARNING] No body found for article: {title}")
            continue

        print(f"Converting article: {title}")
        md_content = clean_article_html(html)
        slug = slugify(title)[:50]
        md_output_path = f"{OUTPUT_DIR}/{slug}.md"
        json_output_path = f"{OUTPUT_DIR}/{slug}.json"

        metadata = {
            "id": article.get("id"),
            "title": article.get("title", "").replace('"', "'"),
            "html_url": article.get("html_url", ""),
            "label_names": article.get("label_names", []),
            "created_at": article.get("created_at"),
            "updated_at": article.get("updated_at"),
            "section_id": article.get("section_id"),
            "content_tag_ids": article.get("content_tag_ids", [])
        }

        frontmatter = (
            f"---\n"
            f"title: \"{metadata['title']}\"\n"
            f"html_url: \"{metadata['html_url']}\"\n"
            f"created_at: \"{metadata['created_at']}\"\n"
            f"updated_at: \"{metadata['updated_at']}\"\n"
            f"labels: {metadata['label_names']}\n"
            f"---\n\n"
        )

        full_content = frontmatter + md_content
        metadata["hash"] = hash_content(full_content)

        try:
            with open(md_output_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            print(f"[SUCCESS] Saved Markdown: {md_output_path}")

            with open(json_output_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            print(f"[SUCCESS] Saved JSON metadata: {json_output_path}")

        except OSError as e:
            print(f"[ERROR] Failed to save files for {slug}: {e}")
            continue

        count += 1

    print(f"Finished writing {count} articles to ./{OUTPUT_DIR}")

# ------------------------- Entry Point -------------------------

if __name__ == "__main__":
    print("Starting scraper using Zendesk API (all articles)...")
    download_and_convert()
    print("Done.")
