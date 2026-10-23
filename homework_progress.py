"""Opt-in homework saves, addressed by a private random resume code."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile

SAVE_DIR = Path(__file__).resolve().parent / "db" / "homework_progress"


def new_code() -> str:
    return secrets.token_hex(16)


def save_path(code: str, directory: Path = SAVE_DIR) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", code):
        raise ValueError("Invalid resume code")
    return directory / (hashlib.sha256(code.encode()).hexdigest() + ".json")


def write_progress(code: str, progress: dict, directory: Path = SAVE_DIR) -> None:
    path = save_path(code, directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "progress": progress}, handle, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_progress(code: str, directory: Path = SAVE_DIR) -> dict:
    data = json.loads(save_path(code, directory).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("progress"), dict):
        raise ValueError("Unsupported progress file")
    progress = data["progress"]
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
    if any(not isinstance(numbers, list) or any(type(n) is not int for n in numbers)
           for numbers in progress.get("completed", {}).values()):
        raise ValueError("Invalid completed questions")
    return progress


def delete_progress(code: str, directory: Path = SAVE_DIR) -> None:
    save_path(code, directory).unlink(missing_ok=True)


def context_id(assignment: str, problem: int, pdf_hash: str, topics: list[str]) -> str:
    """Invalidate old chats when the PDF or allowed curriculum changes."""
    return hashlib.sha256(json.dumps([assignment, problem, pdf_hash, topics],
                                     ensure_ascii=False).encode()).hexdigest()


def focused_question(question: str, number: int) -> str:
    # Always bind generic questions and translated follow-ups to the sidebar choice.
    return f"{question}\n\nSelected homework problem: {number}"
