"""Opt-in homework saves, addressed by a private random resume code."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import re
import secrets
import tempfile

SAVE_DIR = Path(__file__).resolve().parent / "db" / "homework_progress"
BACKUP_LIMIT = 10 * 1024 * 1024


def new_code() -> str:
    return secrets.token_hex(16)


def code_hash(code: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", code):
        raise ValueError("Invalid resume code")
    return hashlib.sha256(code.encode()).hexdigest()


def save_path(code: str, directory: Path | None = None) -> Path:
    if directory is None:
        configured = os.getenv("HOMEWORK_PROGRESS_DIR")
        directory = Path(configured).expanduser() if configured else SAVE_DIR
    return directory / (code_hash(code) + ".json")


def database_url() -> str:
    return os.getenv("HOMEWORK_PROGRESS_DATABASE_URL", "").strip()


@contextmanager
def database_connection(url: str):
    try:
        import psycopg
    except ImportError as exc:
        raise OSError("PostgreSQL progress storage requires psycopg") from exc
    try:
        with psycopg.connect(url, connect_timeout=5) as connection:
            yield connection
    except psycopg.Error as exc:
        raise OSError("PostgreSQL progress storage is unavailable") from exc


@lru_cache(maxsize=1)
def prepare_database(url: str) -> None:
    with database_connection(url) as connection:
        # Serialize first-time schema creation across app instances.
        connection.execute("SELECT pg_advisory_xact_lock(7045026758405221811)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tutor_homework_progress (
                code_hash TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
        """)


def encode_progress(progress: dict) -> str:
    return json.dumps({"version": 1, "progress": progress}, ensure_ascii=False)


def write_progress(code: str, progress: dict, directory: Path | None = None) -> None:
    payload = encode_progress(progress)
    url = database_url() if directory is None else ""
    if url:
        key = code_hash(code)
        prepare_database(url)
        with database_connection(url) as connection:
            connection.execute("""
                INSERT INTO tutor_homework_progress (code_hash, payload) VALUES (%s, %s)
                ON CONFLICT (code_hash) DO UPDATE SET payload = EXCLUDED.payload
            """, (key, payload))
        return

    path = save_path(code, directory)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_progress(code: str, directory: Path | None = None) -> dict:
    url = database_url() if directory is None else ""
    if url:
        key = code_hash(code)
        prepare_database(url)
        with database_connection(url) as connection:
            row = connection.execute(
                "SELECT payload FROM tutor_homework_progress WHERE code_hash = %s", (key,)
            ).fetchone()
        if row is None:
            raise FileNotFoundError("Resume code not found")
        return decode_progress(row[0])
    return decode_progress(save_path(code, directory).read_text(encoding="utf-8"))


def decode_progress(payload: str | bytes) -> dict:
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("progress"), dict):
        raise ValueError("Unsupported progress file")
    progress = data["progress"]
    if ("assignment" in progress and not isinstance(progress["assignment"], str)
            or "question" in progress and type(progress["question"]) is not int):
        raise ValueError("Invalid homework selection")
    if not isinstance(progress.get("conversations", {}), dict) or not isinstance(progress.get("completed", {}), dict):
        raise ValueError("Invalid progress file")
    for conversation in progress.get("conversations", {}).values():
        if not isinstance(conversation, dict):
            raise ValueError("Invalid conversation")
        for field in ("display", "history"):
            messages = conversation.get(field, [])
            if not isinstance(messages, list) or any(
                not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                or not isinstance(m.get("content"), str) for m in messages
            ):
                raise ValueError("Invalid conversation messages")
        for message in conversation.get("display", []):
            sources = message.get("sources", [])
            if not isinstance(sources, list) or any(
                not isinstance(source, dict) or not isinstance(source.get("section"), str)
                or source.get("score") is not None and type(source["score"]) not in (int, float)
                for source in sources
            ):
                raise ValueError("Invalid citation sources")
            if message.get("translation_error") is not None and not isinstance(message["translation_error"], str):
                raise ValueError("Invalid translation error")
    if any(not isinstance(numbers, list) or any(type(n) is not int for n in numbers)
           for numbers in progress.get("completed", {}).values()):
        raise ValueError("Invalid completed questions")
    return progress


def delete_progress(code: str, directory: Path | None = None) -> None:
    url = database_url() if directory is None else ""
    if url:
        key = code_hash(code)
        prepare_database(url)
        with database_connection(url) as connection:
            connection.execute("DELETE FROM tutor_homework_progress WHERE code_hash = %s", (key,))
        return
    save_path(code, directory).unlink(missing_ok=True)


def context_id(assignment: str, problem: int, pdf_hash: str, topics: list[str]) -> str:
    """Invalidate old chats when the PDF or allowed curriculum changes."""
    return hashlib.sha256(json.dumps([assignment, problem, pdf_hash, topics],
                                     ensure_ascii=False).encode()).hexdigest()


def focused_question(question: str, number: int) -> str:
    # Always bind generic questions and translated follow-ups to the sidebar choice.
    return f"{question}\n\nSelected homework problem: {number}"
