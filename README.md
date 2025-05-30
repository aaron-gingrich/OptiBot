OptiBot Mini-Clone
==================

This project is a streamlined clone of the OptiSigns support bot. It scrapes articles from the OptiSigns Zendesk help center, converts them into Markdown with embedded metadata, uploads them to OpenAI's vector store via API, and runs as a daily job to keep the knowledge base up to date.

Setup
-----

### 1. Clone the Repository

```
git clone https://github.com/aaron-gingrich/OptiBot
cd OptiBot
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:

```
cp .env.sample .env
```

Get your OpenAI API key:
1. Go to https://platform.openai.com/playground/
2. Sign up for a free account if you don't have one
3. Click the gear icon (⚙️) in the top right corner
4. Under "Organization", click on "API keys"
5. Click "Create new secret key" to generate your API key

Update `.env` with your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
```

How It Works
------------

### Scraper (`scrape_to_markdown.py`)

- Uses Zendesk's public API to retrieve up to 400 support articles.
- Converts the HTML body of each article to Markdown using `markdownify`.
- Strips out navigation, breadcrumbs, and footers.
- Adds YAML frontmatter metadata including:
  - `title`, `html_url`, `created_at`, `updated_at`, and `label_names`
- Saves each article to the `data/` directory as both `.md` and `.json` files.

### Uploader (`upload_to_openai.py`)

- Reads each Markdown file and calculates a SHA-256 hash.
- Loads `upload_log.json` to detect which files have changed since the last run.
- Uploads only new or updated files using the OpenAI `/files` API.
- Automatically deletes older versions of updated files from OpenAI.
- Attaches the uploaded files to a named vector store.
- Tracks counts of added, updated, and skipped files.
- Saves a run log under `logs/` with timestamped filenames.

### Logging and Summary

After each run, a summary is printed to the console and written to disk:

```
Added:    3
Updated:  2
Skipped: 25
Log file: logs/run_log_YYYYMMDD_HHMMSS.json
```

Docker Usage
------------

This project is Docker-ready and can be scheduled as a recurring job.

### Build the Image

```
docker build -t optibot .
```

### Run the Job

```
docker run -e OPENAI_API_KEY=your-api-key optibot
```

Deployment as Daily Job
------------------------

This project is designed to be deployed as a scheduled job using DigitalOcean App Platform or any other cloud job runner.

Daily job behavior:

- Rescrapes articles from Zendesk
- Compares article hashes to detect changes
- Uploads only the delta (new or updated files)
- Logs the run summary to a timestamped log file

Assistant Usage
---------------

After uploading content, the assistant can answer support questions using the uploaded articles. Example prompt:

```
How do I add a YouTube video?
```

Response should include up to three `Article URL:` citations based on matched context.

Project Structure
-----------------

```
.
├── data/                   # Markdown + JSON output
├── logs/                   # Job run logs
├── scrape_to_markdown.py   # Scraping script
├── upload_to_openai.py     # Upload and vector store management
├── Dockerfile              # For job containerization
├── .env.sample             # Environment variable template
├── README.md
```

Requirements
------------

- Python 3.8+
- OpenAI API key
- Internet access for fetching Zendesk articles and uploading to OpenAI