"""Gọi Gemini qua REST. Không cần SDK, chỉ cần `requests`.

Model đọc từ env GEMINI_MODEL. Tên model đổi theo thời gian nên KHÔNG hardcode cứng:
nếu gặp lỗi 404 thì vào https://ai.google.dev/gemini-api/docs/models chọn model Flash mới nhất.
"""
import json
import os
import re

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"


def _extract_json(text: str):
    """Lấy JSON đầu tiên trong câu trả lời (model hay bọc ```json)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise ValueError("Không thấy JSON trong câu trả lời")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


def generate(prompt: str, *, grounded: bool = False, temperature: float = 0.9, timeout: int = 90):
    """Trả về (text, sources). sources là list {title, url} khi grounded=True."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if grounded:
        body["tools"] = [{"google_search": {}}]
    r = requests.post(
        f"{API_BASE}/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini {r.status_code}: {r.text[:300]}")
    data = r.json()
    cand = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    sources = []
    for ch in cand.get("groundingMetadata", {}).get("groundingChunks", []):
        web = ch.get("web") or {}
        if web.get("uri"):
            sources.append({"title": web.get("title", ""), "url": web["uri"]})
    return text, sources


def generate_json(prompt: str, **kw):
    text, sources = generate(prompt, **kw)
    return _extract_json(text), sources
