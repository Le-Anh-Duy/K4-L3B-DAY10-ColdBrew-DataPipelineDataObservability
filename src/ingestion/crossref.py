from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import html
import logging
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
REQUEST_TIMEOUT_SECONDS = 30
DATE_FIELDS = ("published", "published-online", "published-print", "issued", "created")

_TAG_RE = re.compile(r"<[^>]+>")
_JATS_TITLE_RE = re.compile(r"<jats:title>.*?</jats:title>", re.DOTALL)
_ABSTRACT_LABEL_RE = re.compile(r"^abstract\b[\s:.\-]*", re.IGNORECASE)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def clean_text(value: object) -> str:
    """Bo JATS/HTML tag, decode entity va gom khoang trang."""
    if value is None:
        return ""
    text = _TAG_RE.sub(" ", _JATS_TITLE_RE.sub(" ", str(value)))
    return normalize_whitespace(html.unescape(text))


def clean_summary(value: object) -> str:
    """clean_text + bo nhan 'Abstract' o dau (Crossref hay de lai)."""
    return _ABSTRACT_LABEL_RE.sub("", clean_text(value))


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value.lower() not in seen:
            seen.add(value.lower())
            result.append(value)
    return result


def _date_parts_to_iso(field: dict | None) -> str:
    if not field:
        return ""
    parts = (field.get("date-parts") or [[]])[0] or []
    if parts and parts[0]:
        year, month, day = (list(parts) + [1, 1])[:3]
        return f"{int(year):04d}-{int(month or 1):02d}-{int(day or 1):02d}"
    date_time = field.get("date-time")
    return date_time[:10] if date_time else ""


def _parse_authors(authors: list[dict] | None) -> list[str]:
    names = []
    for author in authors or []:
        name = clean_text(f"{author.get('given', '')} {author.get('family', '')}") or clean_text(author.get("name"))
        names.append(name)
    return unique_ordered(names)


def _pdf_url(item: dict, fallback: str) -> str:
    for link in item.get("link") or []:
        if "pdf" in str(link.get("content-type", "")).lower() and link.get("URL"):
            return link["URL"]
    return fallback


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in payload.get("message", {}).get("items", []):
        paper_id = str(item.get("DOI") or "").strip().lower()
        titles = item.get("title") or []
        title = clean_text(titles[0] if isinstance(titles, list) and titles else titles)
        summary = clean_summary(item.get("abstract"))
        published = next((d for d in (_date_parts_to_iso(item.get(f)) for f in DATE_FIELDS) if d), "")

        if not paper_id or not title or not summary or not published or paper_id in seen_ids:
            logger.warning("Skip invalid/duplicate Crossref item: %s", paper_id or "<no DOI>")
            continue
        seen_ids.add(paper_id)

        categories = unique_ordered([clean_text(subject) for subject in item.get("subject") or []])
        abs_url = item.get("URL") or f"https://doi.org/{paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_parse_authors(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_date_parts_to_iso(item.get("created")) or published,
                abs_url=abs_url,
                pdf_url=_pdf_url(item, abs_url),
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def _request_crossref(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code in RETRY_STATUS_CODES:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt == MAX_ATTEMPTS:
                break
            retry_after = getattr(getattr(error, "response", None), "headers", {}).get("Retry-After", "")
            delay = float(retry_after) if retry_after.isdigit() else 2 ** attempt
            logger.warning("Crossref attempt %d/%d failed (%s); retry in %.0fs", attempt, MAX_ATTEMPTS, error, delay)
            time.sleep(delay)
    raise RuntimeError(f"Crossref API failed after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Lay raw data tu Crossref (REFRESH_SOURCE=1) hoac snapshot local, luu 2 raw artifact."""
    snapshot_path = settings.paths.raw_api_response
    payload: dict | None = None

    if settings.refresh_source or not snapshot_path.exists():
        try:
            payload = _request_crossref(settings)
            write_json(snapshot_path, payload)
        except RuntimeError as error:
            if not snapshot_path.exists():
                raise
            logger.warning("%s -> fallback to local snapshot %s", error, snapshot_path.name)

    if payload is None:
        payload = read_json(snapshot_path)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc raw records JSON; field thieu nhan gia tri mac dinh, field la bi bo qua."""
    list_fields = {"authors", "categories"}
    records = []
    for row in read_json(path):
        values = {}
        for field in fields(PaperRecord):
            value = row.get(field.name)
            if field.name in list_fields:
                values[field.name] = [str(v) for v in value] if isinstance(value, list) else []
            else:
                values[field.name] = "" if value is None else str(value)
        records.append(PaperRecord(**values))
    return records
