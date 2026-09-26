"""Guardrails toi thieu cho chat demo: lam sach input, chan prompt injection, lam sach context, loc output."""

from __future__ import annotations

import re
import secrets

MAX_QUESTION_CHARS = 500
# Canary chen vao system prompt; xuat hien trong output => model dang lo prompt.
CANARY = f"CANARY-{secrets.token_hex(6)}"

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|system|your)\b.{0,20}"
    r"\b(instructions?|prompts?|rules?|messages?)\b",
    r"\b(reveal|show|print|repeat|output|leak|tell me)\b.{0,30}\b(system prompt|hidden prompt|your instructions|"
    r"initial prompt|api[ _-]?key|secret)",
    r"\byou are now\b|\bfrom now on,? you (are|will)\b|\bpretend (to be|you are)\b",
    r"\b(developer mode|jailbreak|do anything now)\b",
    r"</?\s*(system|assistant|user_question|source|history)\s*>",
    r"<\|im_(start|end)\|>|\[/?INST\]",
    r"bỏ qua.{0,20}(hướng dẫn|chỉ dẫn|chỉ thị|lệnh|quy tắc|yêu cầu trước)",
    r"(tiết lộ|cho (tôi|mình) xem|in ra|lặp lại).{0,20}(system prompt|prompt hệ thống|hướng dẫn hệ thống|api ?key|khóa api)",
    r"(từ giờ|bây giờ) (bạn|mày) (là|đóng vai)",
]
_INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.IGNORECASE)
# Chuoi co the lam "vo" ranh gioi prompt neu nam trong du lieu (nguon, lich su).
_DELIMITER_RE = re.compile(r"</?\s*(system|assistant|user_question|source|sources|history)\b[^>]*>|<\|im_(start|end)\|>", re.I)
_SECRET_RE = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|sk-(?:ant-)?[A-Za-z0-9_\-]{20,}")


def clean_user_input(text: str) -> str:
    text = _CONTROL_RE.sub(" ", str(text or ""))
    return re.sub(r"[ \t]+", " ", text).strip()[:MAX_QUESTION_CHARS]


def detect_injection(text: str) -> str | None:
    match = _INJECTION_RE.search(text)
    return match.group(0)[:80] if match else None


def sanitize_context(text: str, limit: int = 1500) -> str:
    """Du lieu (abstract, lich su) dua vao prompt: bo delimiter gia mao, gioi han do dai."""
    return _DELIMITER_RE.sub(" ", _CONTROL_RE.sub(" ", str(text or "")))[:limit]


def safe_url(url: str, fallback: str = "") -> str:
    return url if re.match(r"^https?://", str(url or ""), re.I) else fallback


def guard_output(text: str) -> tuple[str, str]:
    """Tra ve (text da loc, ly do). Lo canary -> thay toan bo cau tra loi."""
    if CANARY in text:
        return "Xin lỗi, mình không thể chia sẻ nội dung đó.", "blocked: system prompt leak"
    redacted = _SECRET_RE.sub("[redacted]", text)
    return redacted, ("redacted secret-like string" if redacted != text else "")
