"""Exam marks-entry deadlines stored in JSON (no database columns)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app

try:
    NAIROBI = ZoneInfo("Africa/Nairobi")
except Exception:
    NAIROBI = timezone(timedelta(hours=3))


def _store_path():
    folder = current_app.instance_path
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "exam_deadlines.json")


def _load():
    path = _store_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data):
    path = _store_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def now_nairobi():
    return datetime.now(NAIROBI)


def parse_due(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=NAIROBI)
    return dt.astimezone(NAIROBI)


def to_iso(dt):
    dt = parse_due(dt)
    return dt.isoformat() if dt else None


def to_local_input(dt):
    dt = parse_due(dt)
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M")


def format_due(dt):
    dt = parse_due(dt)
    if not dt:
        return ""
    return dt.strftime("%d %b %Y, %I:%M %p").lstrip("0").replace(" 0", " ")


def get_deadline(exam_id):
    if exam_id is None:
        return None
    return parse_due(_load().get(str(exam_id)))


def set_deadline(exam_id, due):
    data = _load()
    key = str(exam_id)
    parsed = parse_due(due)
    if parsed is None:
        data.pop(key, None)
    else:
        data[key] = to_iso(parsed)
    _save(data)


def clear_deadline(exam_id):
    set_deadline(exam_id, None)


def is_deadline_passed(exam_id):
    due = get_deadline(exam_id)
    return bool(due and now_nairobi() >= due)


def deadline_payload(exam):
    due = get_deadline(exam.id)
    if not due:
        return {
            "exam_id": exam.id,
            "exam_name": exam.name,
            "due_iso": "",
            "due_local": "",
            "due_label": "",
            "is_closed": False,
            "has_deadline": False,
        }
    closed = now_nairobi() >= due
    return {
        "exam_id": exam.id,
        "exam_name": exam.name,
        "due_iso": to_iso(due),
        "due_local": to_local_input(due),
        "due_label": format_due(due),
        "is_closed": closed,
        "has_deadline": True,
    }


def nearest_open_deadline(exams):
    """Soonest open deadline; if all have passed, the one that closed last."""
    open_ones = []
    closed_ones = []
    for exam in exams:
        if getattr(exam, "is_locked", False):
            continue
        due = get_deadline(exam.id)
        if not due:
            continue
        payload = deadline_payload(exam)
        if payload["is_closed"]:
            closed_ones.append((due, payload))
        else:
            open_ones.append((due, payload))
    if open_ones:
        return min(open_ones, key=lambda item: item[0])[1]
    if closed_ones:
        return max(closed_ones, key=lambda item: item[0])[1]
    return None
