# Company Discovery & Qualification Platform (Phase 1 MVP)

An enterprise-quality, AI-powered system designed to discover and qualify candidate business websites based on user requirements. The platform automates manual market research by converting natural criteria dialogue into optimized search variants, crawling discovered websites, isolating core content body segments, and validating alignment with DeepSeek/Gemini/OpenAI audit checks.

---

## System Flow Architecture

```
User (Dialogue) -> Next.js Chat UI -> Requirement Collector -> Query Generator
                                                                     |
Google Sheets Exporter <- AI Qualification Drawer <- Website Crawler <- Search API (Serper)
```

---

## Project Folder Structure

```
/backend
  /api              # FastAPI App router, Websockets endpoints, and config loader
  /cache            # SQLite cache engine to prevent duplicate domain queries
  /crawler          # Web crawler, indexer logic, and content cleaning
  /models           # Core Pydantic schemas (SearchResult, Company, etc.)
  /prompts          # Plain text template guidelines (chat, search query gen, audit checks)
  /services         # Shared providers (LLM and Search factory layers, Sheets API exporter)

/frontend
  /src/app          # Next.js App Router (layout, dashboard, global styling)
  /src/components   # Chat bubbles, progress logs timeline, results analytics, drawers
  /src/lib          # Client networking modules
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Serper API Key (get a free key at [serper.dev](https://serper.dev))
- LLM Provider Key (DeepSeek API Key, Gemini Key, or OpenAI Key)

---

### Step 1: Backend Setup

1. Open a terminal and navigate to the `/backend` folder:
   ```bash
   cd backend
   ```
2. Create and configure your environment variables file `.env`. (You can copy the template `.env` already present in `/backend/.env`):
   ```env
   LLM_PROVIDER=deepseek
   SEARCH_PROVIDER=serper
   
   SERPER_API_KEY=your_serper_dev_key
   DEEPSEEK_API_KEY=your_deepseek_key
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```

---

### Step 2: Frontend Setup

1. Open a new terminal and navigate to the `/frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open your browser to **`http://localhost:3000`** to run the discovery chat dashboard.

---

## Verification & Fallback Mechanisms

To ensure seamless demonstration in offline or sandbox environments:
1. **Google Search Fallback**: If no `SERPER_API_KEY` is present, the Search Provider logs a warning and automatically returns pre-configured candidate profiles (`Apex Handling`, `Innovate Lifts`, `Eco Water`).
2. **Website Crawling Fallback**: If the sandbox lacks internet or fails DNS lookups, the Web Crawler serves local mock HTML pages mapping the candidate domains.
3. **Google Sheets Fallback**: If no service account JSON parameters are set up in the `.env` file, the Google Sheets engine logs a warning and outputs the final execution audit log to a local file database at `/backend/data/search_{search_id}.json`.
