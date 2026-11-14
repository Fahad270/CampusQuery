# CampusQuery 🎓

### Your College Placement Policy Assistant

**CampusQuery** is a Retrieval-Augmented Generation (RAG) application that helps students and Training & Placement Cell (TPC) members find accurate information from college placement policies through natural-language questions.

Instead of manually searching lengthy policy documents or repeatedly asking TPC coordinators for information, users can ask questions and receive context-aware answers grounded in the uploaded documents.

---

## 💡 The Problem

Placement policies contain important information about eligibility criteria, academic requirements, placement rules, deadlines and other procedures.

However:

- Students often struggle to locate specific information in lengthy policy documents.
- Important rules can be misunderstood or overlooked.
- TPC members handle repeated queries from students.
- Coordinators may also need to refer back to documents to verify specific rules.

**CampusQuery aims to make this information easier to access for both students and TPC members.**

## 🚀 What CampusQuery Does

- **Natural-language Q&A:** Ask placement-related questions in everyday language.
- **Document-grounded responses:** Retrieves relevant policy content before generating an answer.
- **Semantic search:** Finds relevant information based on meaning rather than only exact keyword matches.
- **Source references:** Displays document and page information where available.
- **Persistent vector storage:** Uses ChromaDB to store document embeddings, avoiding unnecessary re-ingestion for every question.
- **Full-stack experience:** React frontend connected to a Flask API.

> Every answer carries a reminder to verify the rule with your **TPC or TR** — the AI can occasionally be wrong, and the official policy document always takes precedence.

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript, CSS |
| Backend | Python, Flask |
| LLM | Google Gemini (`gemini-3.5-flash`, with automatic model fallback) |
| Embeddings | Gemini Embedding Model (`gemini-embedding-001`) |
| RAG Framework | LangChain |
| Vector Database | ChromaDB |
| PDF Processing | PyPDF |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |

## 🧠 How It Works

CampusQuery follows a Retrieval-Augmented Generation architecture.

1. **Document ingestion:** Placement policy PDFs are loaded and split into smaller chunks.
2. **Embedding generation:** Each chunk is converted into a numerical vector using an embedding model.
3. **Vector storage:** The embeddings and associated document metadata are stored in ChromaDB.
4. **User query:** A student enters a placement-related question through the React interface.
5. **Retrieval:** The question is embedded and the top-3 relevant document chunks are retrieved using semantic similarity search.
6. **Answer generation:** Retrieved context and the user's question are passed to Gemini.
7. **Response:** The generated answer and the available source references are returned to the frontend.

```text
             Student / TPC Member
                      |
                      v
              React Frontend
                      |
                 Flask API
                      |
                      v
                User Query
                      |
                      v
             Embedding Model
                      |
                      v
                ChromaDB
              (Top-K Retrieval)
                      |
                      v
             Retrieved Context
                      |
                      v
                 Gemini LLM
                      |
                      v
             Grounded Response
                      |
                      v
              React Frontend
```

## ⚡ Performance Considerations

A key design decision is separating document ingestion from query execution.

- Document embeddings are generated during ingestion, not on every user request.
- The existing ChromaDB collection is loaded for retrieval.
- Only the incoming question needs to be embedded during a query.
- The LLM and vector-store components are reused rather than unnecessarily recreated for every request.
- A SHA-256 manifest (`backend/chroma_db/ingest_manifest.json`) makes ingestion idempotent: re-running `python ingest.py` for the same PDF is a no-op.

This reduces repeated computation and avoids regenerating embeddings for the entire PDF every time someone asks a question.

Verified warm-request timings on the 14-chunk policy collection:

| Phase | Typical |
|---|---|
| Query embedding | ~0.6–0.9 s |
| Chroma top-3 retrieval | ~5–35 ms |
| Gemini generation | ~2–9 s |
| End-to-end API | ~3 s typical |

Generation time varies with Gemini load, so occasional slower answers are expected.

## 🎨 Interface

CampusQuery uses a minimal academic-inspired visual theme.

| Colour | Hex |
|---|---|
| Burgundy | `#800020` |
| White | `#FFFFFF` |
| Blue | `#355C7D` |
| Beige | `#F5F0E8` |

The layout is responsive, keeps the composer anchored, supports `Enter` to send and `Shift + Enter` for a new line, and shows clickable suggested questions.

## 🏗️ Project Structure

```text
CampusQuery/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── styles.css
│   │   └── main.jsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app.py
│   ├── ingest.py
│   ├── query.py
│   ├── requirements.txt
│   ├── Final_Placement_Policy_2026-27.pdf
│   ├── chroma_db/          # committed index + ingestion manifest
│   └── .env                # Gemini API key (never committed)
│
└── README.md
```

## 🔌 API

### `GET /api/health`

Returns `200` when Flask is reachable and the collection contains documents; otherwise `503` with a degraded status.

```json
{
  "status": "ok",
  "backend": { "status": "connected" },
  "vector_db": {
    "status": "connected",
    "collection": "placement_policy",
    "documents": 14,
    "indexed": true
  },
  "models": {
    "embedding": "gemini-embedding-001",
    "generation": "gemini-3.5-flash"
  }
}
```

### `POST /api/chat`

```json
{ "question": "What is the minimum CGPA required for placements?" }
```

```json
{
  "answer": "The placement policy does not mention a minimum CGPA ...",
  "sources": [
    { "document": "Final_Placement_Policy_2026-27.pdf", "page": 2 }
  ]
}
```

Sources come from the retrieved chunks' real metadata. Questions outside the policy receive a grounded "not mentioned" response instead of an invented citation.

Error codes: `400` invalid question, `413` body too large, `502` Gemini failure, `503` index unavailable, `500` unexpected error.

## ⚙️ Running Locally

### Prerequisites

- Python 3
- Node.js and npm
- Google Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/Fahad270/CampusQuery.git
cd CampusQuery
```

### 2. Start the backend

```powershell
.\.venv\Scripts\Activate.ps1        # or create it: python -m venv .venv
pip install -r backend\requirements.txt

cd backend
python app.py
```

The API runs at `http://localhost:5000`.

Add your Gemini key to the existing `backend/.env`:

```text
api_key=YOUR_GEMINI_API_KEY
```

Run document ingestion only when setting up or updating the source documents:

```bash
cd backend
python ingest.py
```

Use `python ingest.py --force` only when you intentionally want to re-embed the document.

### 3. Start the frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. In development the frontend calls `http://localhost:5000` automatically. To point it elsewhere:

```powershell
$env:VITE_API_URL="https://your-backend.onrender.com"
npm run dev
```

Never put the Gemini API key in a `VITE_*` variable — everything prefixed with `VITE_` is shipped to the browser.

## ☁️ Deployment

CampusQuery is designed for separate frontend and backend deployment.

### Frontend — Vercel

- Root directory: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://your-backend.onrender.com`

### Backend — Render

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --workers 1 --threads 4 --timeout 90`
- Environment variables:
  - `FRONTEND_ORIGINS=https://your-app.vercel.app` (optional — CampusQuery already allows `campus-query*.vercel.app` by default)
  - `CHROMA_DIR=/var/data/chroma_db` when a persistent disk is mounted
  - `AUTO_INGEST=true` is not required — the committed index is ready at boot

**Persistence note:** Render's default filesystem is ephemeral, but the built ChromaDB index (about 1.7 MB) is committed in `backend/chroma_db`, so every deploy/restart starts with the 14 policy chunks already indexed. No ingestion and no embedding calls happen during startup, which keeps cold starts fast. If you change the PDF locally, run `python ingest.py` and commit the refreshed `chroma_db` folder. A persistent disk (`CHROMA_DIR=/var/data/chroma_db`) is only needed if you plan to ingest documents at runtime.

**Worker note:** The Gemini and ChromaDB clients are created lazily on the first request, not while the module is imported. ChromaDB holds an open SQLite connection and native state that cannot be inherited across a `fork`, so building the client at import time deadlocks the worker when gunicorn forks after import (for example with `--preload`). Lazy creation means each worker process opens its own healthy connection.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `api_key` | — | Gemini API key (backend `.env`, required) |
| `CHROMA_DIR` | `backend/chroma_db` | Chroma persistence directory |
| `POLICY_PDF` | existing PDF path | Document to ingest |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Primary generation model |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.5-flash-lite,gemini-3.6-flash,gemini-2.5-flash` | Models tried in order when the primary is rate-limited or overloaded |
| `TOP_K` | `3` | Number of retrieved chunks |
| `GEMINI_TIMEOUT` | `45` | Gemini timeout in seconds |
| `GEMINI_MAX_RETRIES` | `1` | SDK retry count |
| `FRONTEND_ORIGINS` | localhost + `campus-query-navy.vercel.app` | Comma-separated CORS origins |
| `FRONTEND_ORIGIN_REGEX` | `campus-query*.vercel.app` | CORS regex for production/preview URLs |
| `AUTO_INGEST` | `false` | Ingest at startup only when the index is missing |
| `LOG_LEVEL` | `INFO` | API log level |
| `PORT` | `5000` | Flask port |

## 🔐 Security & Responsible Usage

- API credentials are stored as backend environment variables and are never sent to the browser.
- Secrets must not be committed to the public repository. `.env`, the virtual environment, `node_modules` and build output are excluded by `.gitignore`.
- Responses should be checked against the original placement policy before being treated as authoritative.
- CampusQuery is an information-access assistant, not a replacement for official TPC communication or policy documents.
- The project does not imply official institutional endorsement.

## ✅ Verification Performed

- Health endpoint returns the real collection and 14 indexed chunks.
- React → Flask → Gemini path returns real answers with real source pages.
- Markdown answers render as headings, lists and bold labels.
- `Enter` submits; `Shift + Enter` inserts a new line.
- Invalid/empty/oversized questions return `400`/`413`.
- Gemini, ChromaDB and unexpected failures map to `502`, `503` and `500` with an error card and retry.
- If a Gemini model is rate-limited (`429`) or overloaded (`503`), the next model in `GEMINI_FALLBACK_MODELS` answers instead. Free-tier quotas are per model per day, so this keeps the assistant available.
- Production build succeeds; layout checked at 390, 768, 1024 and 1440 px without overflow.
- Re-running ingestion skips re-embedding the same PDF.

## 🔮 Future Improvements

- Support multiple policy documents and academic-year versions.
- Improve retrieval quality through evaluation and better chunking strategies.
- Add document upload and controlled re-indexing.
- Introduce feedback collection to evaluate answer quality.
- Add authentication and role-based access for students and TPC members.
- Improve monitoring, response latency and deployment reliability.

## 👨‍💻 About

CampusQuery was developed to address a practical problem in the college placement process: making placement-related information easier to find, understand and access.

The project explores the practical application of **Retrieval-Augmented Generation, semantic search, vector databases, LLMs and full-stack development** to solve a real information-access problem.

---

**Built with React, Flask, LangChain, ChromaDB and Google Gemini.**
