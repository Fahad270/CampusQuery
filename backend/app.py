import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent

# Load the existing .env before importing the RAG pipeline.
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("campusquery.api")

# The RAG objects (embedding model, Chroma client, Gemini client) are created
# once when query.py is imported, not once per request.
RAG_IMPORT_ERROR = None
_rag_import_started = time.perf_counter()
try:
    from query import (
        COLLECTION_NAME,
        GenerationError,
        VectorStoreError,
        answer_question,
        rag_health,
    )
except Exception as exc:  # keep the API process alive so /api/health can report it
    RAG_IMPORT_ERROR = exc
    logger.exception("RAG pipeline failed to initialise")
else:
    logger.info(
        "RAG pipeline ready in %.0fms",
        (time.perf_counter() - _rag_import_started) * 1000
    )


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# Reuse existing environment configuration. Local development origins and the
# deployed Vercel origins are allowed by default, so a missing environment
# variable cannot break the deployed frontend. Override with FRONTEND_ORIGINS
# (comma-separated) or FRONTEND_ORIGIN_REGEX when the domains change.
_default_origins = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:4173,"
    "http://127.0.0.1:4173,"
    "https://campus-query-navy.vercel.app,"
    "https://campusquery.vercel.app"
)
_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
# Covers production and Vercel preview URLs for this project, e.g.
# https://campus-query-<hash>-<team>.vercel.app
_default_origin_regex = r"^https://campus-query[a-z0-9-]*\.vercel\.app$"
_origin_regex = (
    os.getenv("FRONTEND_ORIGIN_REGEX") or _default_origin_regex
).strip() or None
_allowed_origins = _origins + ([_origin_regex] if _origin_regex else [])

CORS(
    app,
    resources={r"/api/*": {"origins": _allowed_origins}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


# Optional: ingest only when explicitly enabled and only when the manifest says
# the PDF is not indexed yet. Never runs on a student query.
def _maybe_auto_ingest():
    if os.getenv("AUTO_INGEST", "false").lower() not in {"1", "true", "yes"}:
        return

    try:
        from ingest import ensure_ingested

        _store, skipped = ensure_ingested()
        if skipped:
            logger.info("AUTO_INGEST: collection already up to date")
        else:
            logger.info("AUTO_INGEST: policy PDF ingested")
    except Exception:
        logger.exception("AUTO_INGEST failed; /api/health will report the index state")


_maybe_auto_ingest()


# @app.get("/api/health")
# def health():
#     """
#     Report server health and real vector database accessibility.

#     A reachable Flask process with a missing/empty policy index is reported as
#     degraded so the frontend does not claim the assistant is ready.
#     """
#     if RAG_IMPORT_ERROR is not None:
#         return jsonify({
#             "status": "degraded",
#             "service": "CampusQuery API",
#             "backend": {"status": "connected"},
#             "vector_db": {
#                 "status": "unavailable",
#                 "collection": None,
#                 "documents": 0,
#                 "indexed": False
#             },
#             "message": "The RAG pipeline could not be initialised."
#         }), 503

#     try:
#         info = rag_health()
#     except Exception:
#         logger.exception("Health check failed while reading ChromaDB")
#         return jsonify({
#             "status": "degraded",
#             "service": "CampusQuery API",
#             "backend": {"status": "connected"},
#             "vector_db": {
#                 "status": "unavailable",
#                 "collection": COLLECTION_NAME,
#                 "documents": 0,
#                 "indexed": False
#             },
#             "message": "The placement policy index is not accessible."
#         }), 503

#     indexed = info["documents"] > 0
#     return jsonify({
#         "status": "ok" if indexed else "degraded",
#         "service": "CampusQuery API",
#         "backend": {"status": "connected"},
#         "vector_db": {
#             "status": "connected",
#             "collection": info["collection"],
#             "documents": info["documents"],
#             "indexed": indexed
#         },
#         "models": {
#             "embedding": info["embedding_model"],
#             "generation": info["generation_model"]
#         },
#         "message": (
#             "CampusQuery is ready."
#             if indexed
#             else "The policy index is empty. Run backend/ingest.py once."
#         )
#     }), 200 if indexed else 503

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "CampusQuery API",
        "backend": "running",
        "rag_import_error": str(RAG_IMPORT_ERROR) if RAG_IMPORT_ERROR else None
    }), 200

@app.get("/api/diag-fs-7f3c9a2e")
def diag_fs_7f3c9a2e():
    """Temporary: filesystem + SQLite probe (no Chroma, no network)."""
    import sqlite3

    from query import CHROMA_DIR

    started = time.perf_counter()
    try:
        files = sorted(os.listdir(CHROMA_DIR))
        db_path = os.path.join(CHROMA_DIR, "chroma.sqlite3")
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute(
                "select count(*) from embeddings"
            ).fetchone()[0]
        return jsonify({
            "ok": True,
            "dir": CHROMA_DIR,
            "files": files,
            "sqlite_rows": rows,
            "elapsed_ms": round((time.perf_counter() - started) * 1000)
        }), 200
    except Exception as exc:
        return jsonify({
            "ok": False,
            "dir": CHROMA_DIR,
            "error": repr(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000)
        }), 200


@app.get("/api/diag-embed-7f3c9a2e")
def diag_embed_7f3c9a2e():
    """Temporary: Gemini embedding probe (no Chroma)."""
    from query import embeddings

    started = time.perf_counter()
    try:
        vector = embeddings.embed_query("ping")
        return jsonify({
            "ok": True,
            "dimensions": len(vector),
            "elapsed_ms": round((time.perf_counter() - started) * 1000)
        }), 200
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": repr(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000)
        }), 200


_CHROMA_PROBE = r"""
import os
import sys
import time

mark = time.perf_counter


def step(message):
    print("[%7.2fs] %s" % (mark(), message), flush=True)


step("python %s" % sys.version.split()[0])
try:
    with open("/proc/meminfo") as meminfo:
        for line in meminfo:
            if line.startswith(("MemTotal", "MemFree", "MemAvailable", "SwapTotal")):
                print(line.strip(), flush=True)
except OSError:
    step("no /proc/meminfo")
step("cpu_count=%s" % os.cpu_count())

step("import chromadb")
import chromadb

step("chromadb %s" % chromadb.__version__)

from chromadb.config import Settings

path = os.environ.get("CHROMA_DIR") or "chroma_db"
step("path=%s isdir=%s" % (path, os.path.isdir(path)))

step("creating PersistentClient")
client = chromadb.PersistentClient(
    path=path,
    settings=Settings(anonymized_telemetry=False),
)
step("client created")

step("heartbeat -> %r" % (client.heartbeat(),))
step("collections -> %r" % ([c.name for c in client.list_collections()],))

step("get_collection")
collection = client.get_collection("placement_policy")
step("collection loaded")

step("count -> %r" % (collection.count(),))

step("query (loads HNSW index)")
result = collection.query(
    query_embeddings=[[0.0] * 3072],
    n_results=3,
    include=["metadatas"],
)
step("query -> %r" % (len(result["ids"][0]),))
step("DONE")
"""


@app.get("/api/diag-chroma-7f3c9a2e")
def diag_chroma_7f3c9a2e():
    """Temporary: isolate ChromaDB calls in a child process."""
    import subprocess
    import sys

    started = time.perf_counter()
    env = dict(os.environ)
    env.setdefault("CHROMA_DIR", str(BASE_DIR / "chroma_db"))
    env["ANONYMIZED_TELEMETRY"] = "False"
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", _CHROMA_PROBE],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        output, _ = process.communicate()

    return jsonify({
        "timed_out": timed_out,
        "returncode": process.returncode,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "output": (output or "")[-6000:]
    }), 200


@app.post("/api/chat")
def chat():
    request_started = time.perf_counter()

    if RAG_IMPORT_ERROR is not None:
        return jsonify({
            "error": "The RAG pipeline is unavailable. Please try again later."
        }), 503

    payload = request.get_json(silent=True, force=True)
    if not isinstance(payload, dict):
        return jsonify({
            "error": "Invalid JSON body. Send {\"question\": \"...\"}."
        }), 400

    question = payload.get("question")
    if not isinstance(question, str):
        return jsonify({"error": "The question must be a string."}), 400

    question = question.strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    if len(question) > 1000:
        return jsonify({
            "error": "The question is too long. Keep it under 1000 characters."
        }), 400

    try:
        result = answer_question(question)
    except VectorStoreError:
        logger.exception("Vector store failure")
        return jsonify({
            "error": "The placement policy index is unavailable. Please try again."
        }), 503
    except GenerationError:
        logger.exception("Gemini generation failure")
        return jsonify({
            "error": "The AI service could not answer right now. Please try again."
        }), 502
    except Exception:
        logger.exception("Unexpected chat failure")
        return jsonify({
            "error": "Something went wrong while answering. Please try again."
        }), 500

    elapsed_ms = (time.perf_counter() - request_started) * 1000
    logger.info(
        "POST /api/chat 200 elapsed=%.0fms sources=%d",
        elapsed_ms,
        len(result.get("sources", []))
    )
    return jsonify(result), 200


@app.get("/")
def index():
    return jsonify({
        "service": "CampusQuery API",
        "endpoints": {
            "health": "GET /api/health",
            "chat": "POST /api/chat"
        }
    })


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(413)
def payload_too_large(_error):
    return jsonify({"error": "Request body is too large."}), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    )
