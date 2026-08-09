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
                    pin_hash TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
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
                    exam_session_id TEXT NOT NULL DEFAULT '',
                    exam_title TEXT NOT NULL DEFAULT '',
                    exam_item_index INTEGER NOT NULL DEFAULT 0,
                    exam_item_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_attempts_created_at ON attempts(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts(student_name);
                CREATE INDEX IF NOT EXISTS idx_lessons_title ON lessons(title);
                """
            )
            # Migrate databases created by earlier DictaType releases.
            student_columns = {row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
            if "pin_hash" not in student_columns:
                conn.execute("ALTER TABLE students ADD COLUMN pin_hash TEXT NOT NULL DEFAULT ''")
            if "active" not in student_columns:
                conn.execute("ALTER TABLE students ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

            attempt_columns = {row[1] for row in conn.execute("PRAGMA table_info(attempts)").fetchall()}
            attempt_migrations = {
                "exam_session_id": "TEXT NOT NULL DEFAULT ''",
                "exam_title": "TEXT NOT NULL DEFAULT ''",
                "exam_item_index": "INTEGER NOT NULL DEFAULT 0",
                "exam_item_count": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, definition in attempt_migrations.items():
                if column not in attempt_columns:
                    conn.execute(f"ALTER TABLE attempts ADD COLUMN {column} {definition}")

            # Link legacy results to a profile when name and class match exactly.
            conn.execute(
                """
                UPDATE attempts
                SET student_id = (
                    SELECT s.id FROM students s
                    WHERE lower(s.name) = lower(attempts.student_name)
                      AND lower(s.class_name) = lower(attempts.class_name)
                    ORDER BY s.id LIMIT 1
                )
                WHERE student_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM students s
                    WHERE lower(s.name) = lower(attempts.student_name)
                      AND lower(s.class_name) = lower(attempts.class_name)
                  )
                """
            )

            defaults = {
                "theme": "light",
                "teacher_pin": hash_pin("1234"),
                "first_run": "1",
                "default_language": "en",
                "window_geometry": "1100x720",
                "security_setup_complete": "0",
                "teacher_auto_lock_minutes": "15",
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

    def list_students(self, active_only: bool = False) -> list[dict[str, Any]]:
        with self.connect() as conn:
            query = """
                SELECT id, name, class_name, identifier, active, created_at
                FROM students
            """
            if active_only:
                query += " WHERE active = 1"
            query += " ORDER BY class_name, name COLLATE NOCASE"
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def get_student(self, student_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, class_name, identifier, active, created_at
                FROM students WHERE id = ?
                """,
                (student_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_student_by_identifier(self, identifier: str) -> dict[str, Any] | None:
        identifier = identifier.strip()
        if not identifier:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, class_name, identifier, active, created_at
                FROM students
                WHERE lower(identifier) = lower(?)
                LIMIT 1
                """,
                (identifier,),
            ).fetchone()
            return dict(row) if row else None

    def find_student(self, name: str, class_name: str = "") -> dict[str, Any] | None:
        name = name.strip()
        class_name = class_name.strip()
        if not name:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, class_name, identifier, active, created_at
                FROM students
                WHERE lower(name) = lower(?) AND lower(class_name) = lower(?)
                ORDER BY id
                LIMIT 1
                """,
                (name, class_name),
            ).fetchone()
            return dict(row) if row else None

    def _next_student_identifier(self, conn: sqlite3.Connection) -> str:
        # Human-readable, non-secret profile identifier. It is not an authentication credential.
        highest = 0
        for row in conn.execute("SELECT identifier FROM students WHERE identifier LIKE 'ST%'").fetchall():
            value = str(row[0] or "").upper()
            if value.startswith("ST") and value[2:].isdigit():
                highest = max(highest, int(value[2:]))
        candidate = highest + 1
        while True:
            identifier = f"ST{candidate:04d}"
            exists = conn.execute(
                "SELECT 1 FROM students WHERE lower(identifier)=lower(?)",
                (identifier,),
            ).fetchone()
            if not exists:
                return identifier
            candidate += 1

    def save_student(
        self,
        name: str,
        class_name: str = "",
        identifier: str = "",
        student_id: int | None = None,
        pin: str | None = None,
        active: bool = True,
    ) -> int:
        """Create or update a student profile.

        ``pin`` is accepted for compatibility with older callers, but student
        profiles no longer require or use a PIN. Teacher access remains protected.
        """
        name = name.strip()
        class_name = class_name.strip()
        identifier = identifier.strip()
        if not name:
            raise ValueError("Student name is required.")
        with self.connect() as conn:
            if student_id is None and not identifier:
                identifier = self._next_student_identifier(conn)
            if identifier:
                params: list[Any] = [identifier]
                query = "SELECT id FROM students WHERE lower(identifier) = lower(?)"
                if student_id is not None:
                    query += " AND id <> ?"
                    params.append(student_id)
                if conn.execute(query, params).fetchone():
                    raise ValueError("That Student ID is already in use.")

            if student_id is None:
                cursor = conn.execute(
                    """
                    INSERT INTO students(name, class_name, identifier, pin_hash, active, created_at)
                    VALUES (?, ?, ?, '', ?, ?)
                    """,
                    (name, class_name, identifier, int(bool(active)), utc_now()),
                )
                result_id = int(cursor.lastrowid)
            else:
                conn.execute(
                    """
                    UPDATE students
                    SET name=?, class_name=?, identifier=?, pin_hash='', active=?
                    WHERE id=?
                    """,
                    (name, class_name, identifier, int(bool(active)), student_id),
                )
                result_id = student_id
        self._link_attempts_to_student(result_id)
        return result_id

    def _link_attempts_to_student(self, student_id: int) -> None:
        student = self.get_student(student_id)
        if not student:
            return
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE attempts
                SET student_id = ?
                WHERE student_id IS NULL
                  AND lower(student_name) = lower(?)
                  AND lower(class_name) = lower(?)
                """,
                (student_id, student.get("name", ""), student.get("class_name", "")),
            )

    def create_student_profile(self, name: str, class_name: str = "") -> dict[str, Any]:
        """Create a student-managed profile without a password or PIN."""
        name = name.strip()
        class_name = class_name.strip()
        if not name:
            raise ValueError("Enter your name.")
        existing = self.find_student(name, class_name)
        if existing:
            if bool(existing.get("active", 1)):
                return existing
            raise ValueError("A matching profile exists but has been disabled by the teacher.")
        student_id = self.save_student(name, class_name, active=True)
        student = self.get_student(student_id)
        if not student:
            raise RuntimeError("The student profile could not be created.")
        return student

    def authenticate_student(self, identifier: str, pin: str = "") -> dict[str, Any] | None:
        """Open an active student profile.

        Student profiles intentionally have no secret credential. The identifier is
        only used to select a profile; it must not be treated as authentication.
        """
        student = self.get_student_by_identifier(identifier)
        if not student or not bool(student.get("active", 1)):
            return None
        return student

    def set_student_pin(self, student_id: int, pin: str) -> None:
        # Compatibility shim for older extensions. Student PINs are no longer used.
        with self.connect() as conn:
            conn.execute("UPDATE students SET pin_hash='' WHERE id=?", (student_id,))

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
                    teacher_comment, exam_session_id, exam_title,
                    exam_item_index, exam_item_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    payload.get("exam_session_id", ""),
                    payload.get("exam_title", ""),
                    int(payload.get("exam_item_index", 0)),
                    int(payload.get("exam_item_count", 0)),
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

    def list_student_attempts(
        self,
        student_id: int | None = None,
        student_name: str = "",
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if student_id is not None:
                student = conn.execute("SELECT name, class_name FROM students WHERE id=?", (student_id,)).fetchone()
                if student:
                    rows = conn.execute(
                        """
                        SELECT * FROM attempts
                        WHERE student_id = ?
                           OR (
                                student_id IS NULL
                                AND lower(student_name) = lower(?)
                                AND lower(class_name) = lower(?)
                           )
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (student_id, student["name"], student["class_name"], limit),
                    ).fetchall()
                else:
                    rows = []
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM attempts
                    WHERE lower(student_name) = lower(?)
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (student_name.strip(), limit),
                ).fetchall()
            return [dict(row) for row in rows]

    def student_history_summary(
        self,
        student_id: int | None = None,
        student_name: str = "",
    ) -> dict[str, Any]:
        attempts = self.list_student_attempts(student_id, student_name)
        scores = [float(item.get("overall_score", 0)) for item in attempts]
        return {
            "attempt_count": len(attempts),
            "average_score": (sum(scores) / len(scores)) if scores else 0.0,
            "best_score": max(scores) if scores else 0.0,
            "latest_at": attempts[0].get("created_at", "") if attempts else "",
        }

    def ensure_student_profile(self, name: str, class_name: str = "") -> dict[str, Any]:
        existing = self.find_student(name, class_name)
        if existing:
            return existing
        return self.create_student_profile(name, class_name)

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
            test_conn.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        finally:
            # sqlite3.Connection's context manager commits/rolls back but does not
            # close the connection. Explicitly close it so Windows releases the
            # backup file before the temporary directory or source is removed.
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
