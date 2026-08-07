from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

APP_NAME = "DictaType"


def utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home()))
    elif sys_platform() == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def sys_platform() -> str:
    import sys

    return sys.platform


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_pin(pin: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", 1)
        candidate = hash_pin(pin, bytes.fromhex(salt_hex)).split(":", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (app_data_dir() / "dictatype.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    category TEXT NOT NULL DEFAULT '',
                    difficulty TEXT NOT NULL DEFAULT 'Intermediate',
                    text TEXT NOT NULL,
                    voice_id TEXT NOT NULL DEFAULT '',
                    voice_name TEXT NOT NULL DEFAULT '',
                    rate INTEGER NOT NULL DEFAULT 175,
                    volume REAL NOT NULL DEFAULT 1.0,
                    replay_limit INTEGER NOT NULL DEFAULT 3,
                    time_limit INTEGER NOT NULL DEFAULT 0,
                    marking_mode TEXT NOT NULL DEFAULT 'balanced',
                    sentence_mode INTEGER NOT NULL DEFAULT 1,
                    speak_punctuation INTEGER NOT NULL DEFAULT 0,
                    show_results INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL DEFAULT '',
                    identifier TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    student_name TEXT NOT NULL,
                    class_name TEXT NOT NULL DEFAULT '',
                    lesson_id INTEGER,
                    lesson_title TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    score_word REAL NOT NULL,
                    score_char REAL NOT NULL,
                    overall_score REAL NOT NULL,
                    wpm REAL NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    replay_count INTEGER NOT NULL,
                    details_json TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'desktop',
                    teacher_comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_attempts_created_at ON attempts(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts(student_name);
                CREATE INDEX IF NOT EXISTS idx_lessons_title ON lessons(title);
                """
            )
            defaults = {
                "theme": "dark",
                "teacher_pin": hash_pin("1234"),
                "first_run": "1",
                "default_language": "en",
                "window_geometry": "1100x720",
            }
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (key, value),
                )
            count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
            if count == 0:
                self._insert_sample_lessons(conn)

    def _insert_sample_lessons(self, conn: sqlite3.Connection) -> None:
        now = utc_now()
        samples = [
            (
                "A Productive Morning",
                "en",
                "General",
                "Beginner",
                "Every morning, Maya opens the classroom windows and prepares the computers. The students arrive quietly, greet one another, and begin their typing exercise.",
            ),
            (
                "Une matinée productive",
                "fr",
                "Général",
                "Débutant",
                "Chaque matin, Maya ouvre les fenêtres de la salle et prépare les ordinateurs. Les élèves arrivent calmement, se saluent et commencent leur exercice de saisie.",
            ),
        ]
        for title, language, category, difficulty, text in samples:
            conn.execute(
                """
                INSERT INTO lessons(
                    title, language, category, difficulty, text,
                    rate, volume, replay_limit, time_limit, marking_mode,
                    sentence_mode, speak_punctuation, show_results,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 175, 1.0, 3, 0, 'balanced', 1, 0, 1, ?, ?)
                """,
                (title, language, category, difficulty, text, now, now),
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def check_pin(self, pin: str) -> bool:
        return verify_pin(pin, self.get_setting("teacher_pin"))

    def set_pin(self, pin: str) -> None:
        self.set_setting("teacher_pin", hash_pin(pin))
        self.set_setting("first_run", "0")

    def list_lessons(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM lessons ORDER BY language, title COLLATE NOCASE"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_lesson(self, lesson_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            return dict(row) if row else None

    def save_lesson(self, data: dict[str, Any], lesson_id: int | None = None) -> int:
        now = utc_now()
        fields = {
            "title": data.get("title", "Untitled lesson").strip() or "Untitled lesson",
            "language": data.get("language", "en"),
            "category": data.get("category", "").strip(),
            "difficulty": data.get("difficulty", "Intermediate"),
            "text": data.get("text", "").strip(),
            "voice_id": data.get("voice_id", ""),
            "voice_name": data.get("voice_name", ""),
            "rate": int(data.get("rate", 175)),
            "volume": float(data.get("volume", 1.0)),
            "replay_limit": int(data.get("replay_limit", 3)),
            "time_limit": int(data.get("time_limit", 0)),
            "marking_mode": data.get("marking_mode", "balanced"),
            "sentence_mode": int(bool(data.get("sentence_mode", True))),
            "speak_punctuation": int(bool(data.get("speak_punctuation", False))),
            "show_results": int(bool(data.get("show_results", True))),
        }
        with self.connect() as conn:
            if lesson_id is None:
                cursor = conn.execute(
                    """
                    INSERT INTO lessons(
                        title, language, category, difficulty, text,
                        voice_id, voice_name, rate, volume, replay_limit,
                        time_limit, marking_mode, sentence_mode,
                        speak_punctuation, show_results, created_at, updated_at
                    ) VALUES (
                        :title, :language, :category, :difficulty, :text,
                        :voice_id, :voice_name, :rate, :volume, :replay_limit,
                        :time_limit, :marking_mode, :sentence_mode,
                        :speak_punctuation, :show_results, :created_at, :updated_at
                    )
                    """,
                    {**fields, "created_at": now, "updated_at": now},
                )
                return int(cursor.lastrowid)
            conn.execute(
                """
                UPDATE lessons SET
                    title=:title, language=:language, category=:category,
                    difficulty=:difficulty, text=:text, voice_id=:voice_id,
                    voice_name=:voice_name, rate=:rate, volume=:volume,
                    replay_limit=:replay_limit, time_limit=:time_limit,
                    marking_mode=:marking_mode, sentence_mode=:sentence_mode,
                    speak_punctuation=:speak_punctuation,
                    show_results=:show_results, updated_at=:updated_at
                WHERE id=:id
                """,
                {**fields, "updated_at": now, "id": lesson_id},
            )
            return lesson_id

    def duplicate_lesson(self, lesson_id: int) -> int:
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")
        lesson["title"] = f"{lesson['title']} (Copy)"
        return self.save_lesson(lesson)

    def delete_lesson(self, lesson_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))

    def list_students(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM students ORDER BY class_name, name COLLATE NOCASE"
            ).fetchall()
            return [dict(row) for row in rows]

    def save_student(
        self,
        name: str,
        class_name: str = "",
        identifier: str = "",
        student_id: int | None = None,
    ) -> int:
        with self.connect() as conn:
            if student_id is None:
                cursor = conn.execute(
                    "INSERT INTO students(name, class_name, identifier, created_at) VALUES (?, ?, ?, ?)",
                    (name.strip(), class_name.strip(), identifier.strip(), utc_now()),
                )
                return int(cursor.lastrowid)
            conn.execute(
                "UPDATE students SET name=?, class_name=?, identifier=? WHERE id=?",
                (name.strip(), class_name.strip(), identifier.strip(), student_id),
            )
            return student_id

    def delete_student(self, student_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))

    def save_attempt(self, payload: dict[str, Any]) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO attempts(
                    student_id, student_name, class_name, lesson_id, lesson_title,
                    answer, score_word, score_char, overall_score, wpm,
                    duration_seconds, replay_count, details_json, source,
                    teacher_comment, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("student_id"),
                    payload.get("student_name", "Anonymous"),
                    payload.get("class_name", ""),
                    payload.get("lesson_id"),
                    payload.get("lesson_title", "Unknown lesson"),
                    payload.get("answer", ""),
                    float(payload.get("score_word", 0)),
                    float(payload.get("score_char", 0)),
                    float(payload.get("overall_score", 0)),
                    float(payload.get("wpm", 0)),
                    int(payload.get("duration_seconds", 0)),
                    int(payload.get("replay_count", 0)),
                    json.dumps(payload.get("details", {}), ensure_ascii=False),
                    payload.get("source", "desktop"),
                    payload.get("teacher_comment", ""),
                    utc_now(),
                ),
            )
            return int(cursor.lastrowid)

    def list_attempts(self, limit: int = 1000) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM attempts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_attempt(self, attempt_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["details"] = json.loads(item.pop("details_json"))
            except Exception:
                item["details"] = {}
            return item

    def update_attempt_comment(self, attempt_id: int, comment: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE attempts SET teacher_comment = ? WHERE id = ?",
                (comment.strip(), attempt_id),
            )

    def delete_attempt(self, attempt_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM attempts WHERE id = ?", (attempt_id,))

    def backup(self, destination: Path) -> Path:
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            backup_conn = sqlite3.connect(destination)
            try:
                conn.backup(backup_conn)
            finally:
                backup_conn.close()
        return destination

   def restore(self, source: Path) -> None:
        source = source.expanduser().resolve()

        if not source.exists():
            raise FileNotFoundError(source)

        test_conn = sqlite3.connect(source)

        try:
            test_conn.execute(
                "SELECT name FROM sqlite_master LIMIT 1"
            ).fetchone()
        finally:
            test_conn.close()

        shutil.copy2(source, self.path)

        for suffix in ("-wal", "-shm"):
            stale = Path(str(self.path) + suffix)

            if stale.exists():
                stale.unlink()

        self.initialize()

    def export_lessons(self, lesson_ids: Iterable[int] | None = None) -> list[dict[str, Any]]:
        lessons = self.list_lessons()
        if lesson_ids is None:
            return lessons
        wanted = {int(value) for value in lesson_ids}
        return [lesson for lesson in lessons if lesson["id"] in wanted]

    def import_lessons(self, lessons: Iterable[dict[str, Any]]) -> int:
        count = 0
        for lesson in lessons:
            if not str(lesson.get("text", "")).strip():
                continue
            self.save_lesson(lesson)
            count += 1
        return count
