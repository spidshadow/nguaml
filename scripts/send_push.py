"""Gửi web push tới điện thoại. Phần riêng tư (họp/email/task) đi trong payload đã mã hoá end-to-end.

Env:
  VAPID_PRIVATE_KEY   khoá riêng dạng base64url (tạo ở docs/setup.html)
  PUSH_SUBSCRIPTIONS  JSON: 1 object hoặc 1 mảng subscription lấy từ app trên điện thoại
  DRY_RUN=1           chỉ in payload, không gửi
"""
import json
import os
import sys
from pathlib import Path

from pywebpush import WebPushException, webpush

ROOT = Path(__file__).resolve().parent.parent
MAX_PAYLOAD = 3000  # giới hạn web push ~4KB, chừa biên an toàn


def log(msg):
    print(f"[push] {msg}", file=sys.stderr)


def build_payload(public, private, app_url):
    q = public["quote"]["text"]
    parts = []
    if private.get("meetings"):
        parts.append(f"{len(private['meetings'])} họp")
    if private.get("emails"):
        parts.append(f"{len(private['emails'])} email")
    if private.get("tasks"):
        parts.append(f"{len(private['tasks'])} task")
    body = q if len(q) <= 110 else q[:107] + "..."
    if parts:
        body += "\n" + " · ".join(parts)
    elif public.get("schedule"):
        body += f"\n{len(public['schedule'])} trận hôm nay"

    payload = {
        "title": f"Bản tin Ngựa ml · {public['date_label']}",
        "body": body,
        "url": app_url,
        "date": public["date"],
        "private": {k: private.get(k, []) for k in ("meetings", "emails", "tasks")},
    }
    # Cắt bớt phần private nếu quá dài
    while len(json.dumps(payload, ensure_ascii=False).encode()) > MAX_PAYLOAD:
        longest = max(payload["private"], key=lambda k: len(payload["private"][k]))
        if not payload["private"][longest]:
            break
        payload["private"][longest].pop()
    return payload


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    public = json.loads((ROOT / "docs/brief/today.json").read_text(encoding="utf-8"))
    pp = ROOT / ".private/private.json"
    private = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {}
    payload = build_payload(public, private, cfg["app_url"])

    if os.environ.get("DRY_RUN") == "1":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        log(f"payload {len(json.dumps(payload, ensure_ascii=False).encode())} bytes")
        return

    raw = os.environ.get("PUSH_SUBSCRIPTIONS", "").strip()
    key = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not raw or not key:
        log("Thiếu PUSH_SUBSCRIPTIONS hoặc VAPID_PRIVATE_KEY, bỏ qua bước gửi push")
        sys.exit(1)
    subs = json.loads(raw)
    subs = subs if isinstance(subs, list) else [subs]

    ok = 0
    for i, sub in enumerate(subs, 1):
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=key,
                vapid_claims={"sub": cfg.get("push_contact", "mailto:you@example.com")},
                ttl=6 * 3600,
            )
            ok += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            log(f"thiết bị #{i} lỗi {status}: {e}")
            if status in (404, 410):
                log("Subscription đã hết hạn, hãy bật lại thông báo trong app và cập nhật secret.")
    log(f"đã gửi {ok}/{len(subs)} thiết bị")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
