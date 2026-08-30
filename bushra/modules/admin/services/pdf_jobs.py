"""Filesystem job store for background class report-card PDFs."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
import time
import traceback
from multiprocessing import get_context
from pathlib import Path


JOB_TTL_SECONDS = 60 * 60


def _job_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "bushrasms-reportcards"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.json"


def pdf_path(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.pdf"


def cleanup_old_jobs(max_age=JOB_TTL_SECONDS):
    cutoff = time.time() - max_age
    for path in _job_dir().glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                pdf_path(path.stem).unlink(missing_ok=True)
        except OSError:
            continue


def create_job(user_id: int, filename: str) -> str:
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


def start_class_pdf_process(job_id: str, params: dict):
    """
    Run WeasyPrint off the HTTP request so gunicorn/nginx do not time out
    the teacher’s tab. Prefer a spawned process; fall back to a thread.
    """
    try:
        ctx = get_context("spawn")
        process = ctx.Process(
            target=run_reportcard_job,
            args=(job_id, params),
            daemon=False,
        )
        process.start()
        return process
    except Exception:
        traceback.print_exc()
        thread = threading.Thread(
            target=run_reportcard_job,
            args=(job_id, params),
            daemon=True,
        )
        thread.start()
        return thread


def run_reportcard_job(job_id: str, params: dict):
    os.environ.setdefault("BUSHRA_PDF_JOB", "1")
    try:
        from .... import create_app

        app = create_app()
        with app.app_context():
            from .report_pdf import render_class_report_pdf

            write_job(job_id, status="running", message="Preparing report data…")
            pdf_bytes, filename = render_class_report_pdf(
                params,
                on_progress=lambda done, total, message: write_job(
                    job_id,
                    done=done,
                    total=total,
                    message=message,
                ),
            )
            pdf_path(job_id).write_bytes(pdf_bytes)
            write_job(
                job_id,
                status="ready",
                filename=filename,
                message="Ready",
            )
    except Exception:
        traceback.print_exc()
        try:
            write_job(
                job_id,
                status="error",
                error="Failed to generate PDF. Please try again.",
                message="Failed",
            )
        except Exception:
            pass

