"""Nguồn dữ liệu riêng tư: lịch họp, email, task. Dữ liệu này KHÔNG được commit lên repo.

Mỗi nguồn chạy độc lập, lỗi một nguồn không làm hỏng cả bản tin.
Chỉ dùng quyền ĐỌC (readonly). Secret cần có (tuỳ nguồn bạn bật):
  Google : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
  Outlook: MS_CLIENT_ID, MS_REFRESH_TOKEN, (MS_TENANT mặc định 'common', MS_CLIENT_SECRET nếu app là confidential)
"""
import os
import sys
from datetime import datetime, timedelta

import requests

TIMEOUT = 30


def _log(msg):
    print(f"[private] {msg}", file=sys.stderr)


# ---------- Google ----------
def _google_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def google_calendar(tok, day_start, day_end, limit):
    r = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {tok}"},
        params={
            "timeMin": day_start.isoformat(),
            "timeMax": day_end.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": limit,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for ev in r.json().get("items", []):
        start = ev.get("start", {})
        if "dateTime" in start:
            t = datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
        else:
            t = "Cả ngày"
        out.append({"time": t, "title": ev.get("summary", "(không tiêu đề)"), "source": "Google Calendar"})
    return out


def gmail_unread(tok, query, limit):
    h = {"Authorization": f"Bearer {tok}"}
    r = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=h,
        params={"q": query, "maxResults": limit},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for m in r.json().get("messages", []):
        d = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
            headers=h,
            params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
            timeout=TIMEOUT,
        )
        d.raise_for_status()
        hdr = {x["name"]: x["value"] for x in d.json().get("payload", {}).get("headers", [])}
        sender = hdr.get("From", "").split("<")[0].strip().strip('"')
        out.append({"from": sender, "subject": hdr.get("Subject", "(không tiêu đề)"), "source": "Gmail"})
    return out


def google_sheet_tasks(tok, cfg, today, limit):
    sid = cfg.get("spreadsheet_id")
    if not sid:
        return []
    r = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{cfg['range']}",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    rows = r.json().get("values", [])
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    try:
        i_date = header.index(cfg["date_column"])
        i_title = header.index(cfg["title_column"])
    except ValueError:
        _log(f"Sheet không có cột '{cfg['date_column']}' hoặc '{cfg['title_column']}'. Header: {header}")
        return []
    i_status = header.index(cfg["status_column"]) if cfg.get("status_column") in header else None
    done = {v.lower() for v in cfg.get("done_values", [])}
    last_day = today + timedelta(days=int(cfg.get("look_ahead_days", 0)))
    out = []
    for row in rows[1:]:
        cell = lambda i: row[i].strip() if i is not None and i < len(row) else ""
        try:
            d = datetime.strptime(cell(i_date), cfg["date_format"]).date()
        except ValueError:
            continue
        if not (today <= d <= last_day):
            continue
        if i_status is not None and cell(i_status).lower() in done:
            continue
        out.append({"title": cell(i_title), "due": d.strftime("%d/%m"), "source": "Google Sheet"})
    return out[:limit]


# ---------- Outlook / Microsoft Graph ----------
def _ms_token():
    tenant = os.environ.get("MS_TENANT", "common")
    data = {
        "client_id": os.environ["MS_CLIENT_ID"],
        "grant_type": "refresh_token",
        "refresh_token": os.environ["MS_REFRESH_TOKEN"],
        "scope": "https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/Mail.Read offline_access",
    }
    if os.environ.get("MS_CLIENT_SECRET"):
        data["client_secret"] = os.environ["MS_CLIENT_SECRET"]
    r = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=data, timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()["access_token"]


def outlook_calendar(tok, day_start, day_end, limit):
    r = requests.get(
        "https://graph.microsoft.com/v1.0/me/calendarView",
        headers={"Authorization": f"Bearer {tok}", "Prefer": 'outlook.timezone="Asia/Bangkok"'},
        params={
            "startDateTime": day_start.isoformat(),
            "endDateTime": day_end.isoformat(),
            "$orderby": "start/dateTime",
            "$top": limit,
            "$select": "subject,start,isAllDay",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for ev in r.json().get("value", []):
        t = "Cả ngày" if ev.get("isAllDay") else ev["start"]["dateTime"][11:16]
        out.append({"time": t, "title": ev.get("subject", "(không tiêu đề)"), "source": "Outlook"})
    return out


def outlook_mail(tok, limit):
    r = requests.get(
        "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
        headers={"Authorization": f"Bearer {tok}"},
        params={
            "$filter": "isRead eq false",
            "$top": limit,
            "$select": "subject,from,receivedDateTime",
            "$orderby": "receivedDateTime desc",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for m in r.json().get("value", []):
        sender = m.get("from", {}).get("emailAddress", {}).get("name", "")
        out.append({"from": sender, "subject": m.get("subject", "(không tiêu đề)"), "source": "Outlook"})
    return out


# ---------- Tổng hợp ----------
def collect(cfg, now):
    """cfg = config['private'], now = datetime có timezone. Trả về dict meetings/emails/tasks."""
    enabled = set(cfg.get("enabled_sources", []))
    limit = int(cfg.get("max_items_each", 5))
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    result = {"meetings": [], "emails": [], "tasks": [], "errors": []}

    def run(name, fn, bucket):
        if name not in enabled:
            return
        try:
            result[bucket].extend(fn())
        except KeyError as e:
            _log(f"{name}: thiếu secret {e}, bỏ qua")
        except Exception as e:  # noqa: BLE001 - muốn nuốt mọi lỗi nguồn riêng lẻ
            _log(f"{name}: lỗi {type(e).__name__}: {e}")
            result["errors"].append(name)

    gtok = None
    if enabled & {"google_calendar", "gmail", "google_sheet"} and os.environ.get("GOOGLE_REFRESH_TOKEN"):
        try:
            gtok = _google_token()
        except Exception as e:  # noqa: BLE001
            _log(f"google token: {e}")
            result["errors"].append("google_token")
    if gtok:
        run("google_calendar", lambda: google_calendar(gtok, day_start, day_end, limit), "meetings")
        run("gmail", lambda: gmail_unread(gtok, cfg.get("gmail_query", "is:unread newer_than:1d"), limit), "emails")
        run("google_sheet", lambda: google_sheet_tasks(gtok, cfg.get("sheet", {}), now.date(), limit), "tasks")

    mtok = None
    if enabled & {"outlook_calendar", "outlook_mail"} and os.environ.get("MS_REFRESH_TOKEN"):
        try:
            mtok = _ms_token()
        except Exception as e:  # noqa: BLE001
            _log(f"ms token: {e}")
            result["errors"].append("ms_token")
    if mtok:
        run("outlook_calendar", lambda: outlook_calendar(mtok, day_start, day_end, limit), "meetings")
        run("outlook_mail", lambda: outlook_mail(mtok, limit), "emails")

    result["meetings"].sort(key=lambda m: (m["time"] == "Cả ngày", m["time"]))
    return result
