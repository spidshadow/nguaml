"""Tạo bản tin hằng ngày.

Ghi 2 file:
  docs/brief/today.json      -> CÔNG KHAI (quote, tin tức, lịch đấu, joke), commit lên repo
  .private/private.json      -> RIÊNG TƯ (họp, email, task), KHÔNG commit, chỉ đi qua push đã mã hoá

Env:
  GEMINI_API_KEY, GEMINI_MODEL  (bắt buộc trừ khi DRY_RUN=1)
  DRY_RUN=1                     (dùng dữ liệu giả, không gọi API)
"""
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gemini_client  # noqa: E402
import private_sources  # noqa: E402

DRY = os.environ.get("DRY_RUN") == "1"
WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def log(msg):
    print(f"[build] {msg}", file=sys.stderr)


def load(path, default=None):
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def pick_quote(quotes, state, rng):
    """Chọn ngẫu nhiên, không lặp cho tới khi dùng hết cả thư viện."""
    used = set(state.get("used_quote_ids", []))
    pool = [q for q in quotes if q["id"] not in used]
    if not pool:
        pool, used = quotes, set()
    q = rng.choice(pool)
    state["used_quote_ids"] = sorted(used | {q["id"]})
    img = f"img/quote-{q['id']:02d}.png"
    q = dict(q)
    q["image"] = img if (ROOT / "docs" / img).exists() else None
    return q


def get_news(cfg, today_str):
    if DRY:
        return {
            "headlines": [
                {"category": "LCP", "title": "(Mẫu) Đội A thắng đội B 2-1", "summary": "Tóm tắt mẫu.", "source": "Nguồn mẫu"},
                {"category": "Bóng đá", "title": "(Mẫu) Tin bóng đá", "summary": "Tóm tắt mẫu.", "source": "Nguồn mẫu"},
            ],
            "schedule": [
                {"time": "17:00", "league": "LCP", "match": "(Mẫu) Đội A vs Đội B"},
                {"time": "20:00", "league": "Bóng đá", "match": "(Mẫu) CLB X vs CLB Y"},
            ],
        }, [{"title": "Nguồn mẫu", "url": "https://example.com"}]

    topics = "\n".join(f"- {t}" for t in cfg["news"]["topics"])
    focus = "\n".join(f"- {t}" for t in cfg["schedule"]["focus"])
    prompt = f"""Hôm nay là {today_str} (giờ Việt Nam). Dùng Google Search để tìm thông tin MỚI NHẤT (24-48 giờ qua).

Nhiệm vụ 1: chọn tối đa {cfg['news']['max_items']} tin đáng chú ý nhất thuộc các chủ đề:
{topics}

Nhiệm vụ 2: liệt kê lịch thi đấu diễn ra TRONG NGÀY HÔM NAY theo giờ Việt Nam (UTC+7), thuộc:
{focus}
Tối đa {cfg['schedule']['max_items']} trận. Nếu không tìm thấy lịch đáng tin cậy cho mục nào thì bỏ qua, KHÔNG được đoán.

Yêu cầu: tiếng Việt tự nhiên, giữ nguyên thuật ngữ esports tiếng Anh (jungler, draft, patch...). Mỗi tin summary tối đa 25 từ.
Chỉ trả về JSON hợp lệ, không thêm chữ nào khác, đúng cấu trúc:
{{"headlines":[{{"category":"","title":"","summary":"","source":"tên báo/trang"}}],
  "schedule":[{{"time":"HH:MM","league":"","match":""}}]}}"""
    return gemini_client.generate_json(prompt, grounded=True, temperature=0.3)


def get_joke(cfg, recent, rng):
    fallback = load("data/jokes.json", [])
    if DRY:
        return rng.choice(fallback)
    avoid = "\n".join(f"- {j}" for j in recent[-14:]) or "(chưa có)"
    prompt = f"""Viết 1 câu joke tiếng Việt, phong cách: {cfg['joke']['style']}.
Tối đa 2-3 câu. Không trùng ý với các joke gần đây:
{avoid}
Chỉ trả về JSON: {{"joke":"..."}}"""
    try:
        data, _ = gemini_client.generate_json(prompt, temperature=1.0)
        return data["joke"].strip()
    except Exception as e:  # noqa: BLE001
        log(f"joke lỗi ({e}), dùng joke dự phòng")
        return rng.choice([j for j in fallback if j not in recent] or fallback)


def main():
    cfg = load("config.json")
    tz = ZoneInfo(cfg["timezone"])
    now = datetime.now(tz)
    today_str = f"{WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}"
    rng = random.Random()

    state = load("data/state.json", {"used_quote_ids": [], "recent_jokes": []})
    quote = pick_quote(load("data/quotes.json"), state, rng)

    news, sources = {"headlines": [], "schedule": []}, []
    try:
        news, sources = get_news(cfg, today_str)
    except Exception as e:  # noqa: BLE001
        log(f"tin tức lỗi: {e}")
        news["error"] = True

    joke = get_joke(cfg, state.get("recent_jokes", []), rng)
    state["recent_jokes"] = (state.get("recent_jokes", []) + [joke])[-30:]

    public = {
        "date": now.strftime("%Y-%m-%d"),
        "date_label": today_str,
        "generated_at": now.isoformat(timespec="seconds"),
        "quote": quote,
        "headlines": news.get("headlines", []),
        "schedule": news.get("schedule", []),
        "sources": sources[:8],
        "news_failed": bool(news.get("error")),
        "joke": joke,
    }
    (ROOT / "docs/brief").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/brief/today.json").write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "data/state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if DRY:
        private = {
            "meetings": [{"time": "09:30", "title": "(Mẫu) Họp content tuần", "source": "Google Calendar"}],
            "emails": [{"from": "Đối tác A", "subject": "(Mẫu) Duyệt key visual", "source": "Gmail"}],
            "tasks": [{"title": "(Mẫu) Lên checklist preheat", "due": now.strftime("%d/%m"), "source": "Google Sheet"}],
            "errors": [],
        }
    else:
        private = private_sources.collect(cfg.get("private", {}), now)
    (ROOT / ".private").mkdir(exist_ok=True)
    (ROOT / ".private/private.json").write_text(json.dumps(private, ensure_ascii=False, indent=2), encoding="utf-8")
    log(
        f"OK: {len(public['headlines'])} tin, {len(public['schedule'])} trận, "
        f"{len(private['meetings'])} họp, {len(private['emails'])} email, {len(private['tasks'])} task"
    )


if __name__ == "__main__":
    main()
