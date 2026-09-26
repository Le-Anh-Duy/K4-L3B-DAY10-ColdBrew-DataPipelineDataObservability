"""Demo chat ve paper corpus: guardrails + router + RAG tren ChromaDB, nho theo session, tuy chon Crossref live.

Chay: .venv\\Scripts\\python demo/server.py  ->  mo http://127.0.0.1:8000
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import uuid

import pandas as pd
import requests

from core.config import load_settings, normalized_provider
from ingestion.crossref import CROSSREF_WORKS_URL, parse_crossref_payload
from retrieval.chat import SessionStore, chat
from retrieval.index import LocalEmbeddingIndex

HOST, PORT = "127.0.0.1", 8000  # chi nghe localhost
MAX_BODY_BYTES = 8 * 1024
INDEX_HTML = Path(__file__).with_name("index.html")
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

settings = load_settings()
sessions = SessionStore()


def load_index() -> LocalEmbeddingIndex:
    if settings.paths.embeddings_json.exists():
        try:
            return LocalEmbeddingIndex.load(settings)
        except Exception:
            pass  # manifest cu / collection bi xoa -> build lai
    return LocalEmbeddingIndex.build(pd.read_json(settings.paths.clean_json), settings)


def search_crossref(query: str, rows: int = 3) -> tuple[list[dict], str]:
    try:
        response = requests.get(
            CROSSREF_WORKS_URL,
            params={"query.bibliographic": query, "filter": "has-abstract:true", "rows": rows},
            timeout=15,
        )
        response.raise_for_status()
        records = parse_crossref_payload(response.json())
    except Exception as error:
        return [], f"Không gọi được Crossref ({type(error).__name__})."
    return [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "authors": ", ".join(r.authors),
            "published": r.published,
            "summary": r.summary,
            "url": r.abs_url,
        }
        for r in records
    ], ""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._json(413, {"error": "request too large"})
            return None
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:  # JSON sai hoac body khong phai UTF-8
            self._json(400, {"error": "invalid JSON"})
            return None
        if not isinstance(body, dict):
            self._json(400, {"error": "invalid JSON"})
            return None
        return body

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/stats":
            self._json(
                200,
                {
                    "docs": len(INDEX.documents),
                    "collection": INDEX.collection_name,
                    "llm": f"{normalized_provider(settings)} / {settings.model_name}",
                },
            )
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in ("/api/ask", "/api/reset"):
            return self._json(404, {"error": "not found"})
        body = self._read_json()
        if body is None:
            return
        session_id = str(body.get("session_id", "")).lower()
        if not _SESSION_ID_RE.match(session_id):
            session_id = str(uuid.uuid4())

        if self.path == "/api/reset":
            sessions.reset(session_id)
            return self._json(200, {"session_id": session_id, "ok": True})

        session = sessions.get(session_id)
        result = chat(
            str(body.get("question", "")),
            session,
            settings,
            INDEX,
            internet=bool(body.get("internet")),
            web_search=search_crossref,
        )
        result.update(session_id=session_id, memory_turns=len(session.turns))
        self._json(429 if result["route"] == "rate_limited" else 200, result)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[demo] {self.command} {self.path} {args[1] if len(args) > 1 else ''}")


if __name__ == "__main__":
    print("Loading index...")
    INDEX = load_index()
    print(f"Index {INDEX.collection_name}: {len(INDEX.documents)} docs. Open http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
