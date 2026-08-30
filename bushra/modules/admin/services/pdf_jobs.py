"""Filesystem job store for class report-card PDFs.

Work runs on status polls, not in a background process. PythonAnywhere
kills subprocesses/threads when the web request that started them ends.
"""

from __future__ import annotations

import json
import os
import pickle
import secrets
import tempfile
import time
import traceback
from pathlib import Path

from .pdf_render import html_to_pdf_bytes, merge_pdf_bytes
from .report_pdf import (
    CHUNK_SIZE,
    build_report_bundle,
    render_chunk_pdf,
    row_count,
    snapshot_bundle,
)


JOB_TTL_SECONDS = 60 * 60
LOCK_STALE_SECONDS = 180


def _job_dir() -> Path:
    if os.environ.get("PYTHONANYWHERE_DOMAIN") or os.environ.get("PYTHONANYWHERE_SITE"):
        root = Path(os.environ.get("HOME") or ".") / "bushrasms-reportcards"
    else:
        root = Path(tempfile.gettempdir()) / "bushrasms-reportcards"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _meta_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.json"


def _bundle_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.pkl"


def _lock_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.lock"


def _part_path(job_id: str, index: int) -> Path:
    return _job_dir() / f"{job_id}.part{index}.pdf"


def pdf_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.pdf"


def cleanup_old_jobs(max_age=JOB_TTL_SECONDS):
    cutoff = time.time() - max_age
    for path in _job_dir().iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def create_job(user_id: int, filename: str, params: dict | None = None) -> str:
    cleanup_old_jobs()
    job_id = secrets.token_urlsafe(16)
    write_job(
        job_id,
        status="queued",
        user_id=int(user_id),
        filename=filename,
        error=None,
        done=0,
        total=0,
        next_index=0,
        part_count=0,
        prepared=False,
        params=params or {},
        message="Queued…",
    )
    return job_id


def write_job(job_id: str, **fields):
    path = _meta_path(job_id)
    meta = read_job(job_id) or {}
    meta.update(fields)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta), encoding="utf-8")
    tmp.replace(path)


def read_job(job_id: str) -> dict | None:
    path = _meta_path(job_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _acquire_lock(job_id: str) -> bool:
    path = _lock_path(job_id)
    now = time.time()
    try:
        if path.exists() and now - path.stat().st_mtime > LOCK_STALE_SECONDS:
            path.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(now).encode("ascii"))
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock(job_id: str):
    _lock_path(job_id).unlink(missing_ok=True)


def advance_class_pdf_job(job_id: str) -> dict | None:
    """
    Do the next slice of work inside this HTTP request, then return status.
    Safe on PythonAnywhere because nothing has to outlive the request.
    """
    meta = read_job(job_id)
    if not meta or meta.get("status") in ("ready", "error"):
        return meta
    if not _acquire_lock(job_id):
        return meta

    try:
        if not meta.get("prepared"):
            bundle = snapshot_bundle(build_report_bundle(**meta.get("params") or {}))
            _bundle_path(job_id).write_bytes(pickle.dumps(bundle, protocol=4))
            total = row_count(bundle)
            write_job(
                job_id,
                status="running",
                prepared=True,
                total=total,
                next_index=0,
                part_count=0,
                done=0,
                filename=bundle.get("filename") or meta.get("filename"),
                message=f"Generating PDF (0 of {total})…",
            )
            return read_job(job_id)

        bundle = pickle.loads(_bundle_path(job_id).read_bytes())
        next_index = int(meta.get("next_index") or 0)
        total = int(meta.get("total") or row_count(bundle))
        if next_index >= total:
            _finalize_job(job_id, meta)
            return read_job(job_id)

        pdf_bytes, next_index, total = render_chunk_pdf(bundle, next_index)
        part_count = int(meta.get("part_count") or 0)
        _part_path(job_id, part_count).write_bytes(pdf_bytes)
        part_count += 1
        done = min(total, next_index)

        if next_index >= total:
            write_job(
                job_id,
                next_index=next_index,
                part_count=part_count,
                done=done,
                total=total,
                message=f"Generating PDF ({done} of {total})…",
            )
            _finalize_job(job_id, read_job(job_id))
        else:
            write_job(
                job_id,
                status="running",
                next_index=next_index,
                part_count=part_count,
                done=done,
                total=total,
                message=f"Generating PDF ({done} of {total})…",
            )
        return read_job(job_id)
    except Exception:
        traceback.print_exc()
        write_job(
            job_id,
            status="error",
            error="Failed to generate PDF. Please try again.",
            message="Failed",
        )
        return read_job(job_id)
    finally:
        _release_lock(job_id)


def _finalize_job(job_id: str, meta: dict):
    part_count = int((meta or {}).get("part_count") or 0)
    parts = []
    for index in range(part_count):
        path = _part_path(job_id, index)
        if path.exists():
            parts.append(path.read_bytes())
    pdf_path(job_id).write_bytes(merge_pdf_bytes(parts))
    write_job(
        job_id,
        status="ready",
        done=int((meta or {}).get("total") or 0),
        message="Ready",
    )
    _bundle_path(job_id).unlink(missing_ok=True)
    for index in range(part_count):
        _part_path(job_id, index).unlink(missing_ok=True)
