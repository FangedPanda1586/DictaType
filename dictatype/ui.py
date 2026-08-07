from __future__ import annotations

import csv
import html
import json
import os
import queue
import subprocess
import sys
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable

from .classroom import ClassroomServer
from .db import Database, app_data_dir
from .scoring import calculate_wpm, score_text, split_sentences
from .tts import SpeechEngine, Voice, list_voices, verbalize_punctuation

APP_TITLE = "DictaType"
APP_VERSION = "1.0.0"

DARK = {
    "bg": "#0b1020",
    "panel": "#151c33",
    "panel2": "#202a48",
    "field": "#0f162a",
    "border": "#303c63",
    "text": "#f3f6ff",
    "muted": "#aeb8d1",
    "accent": "#7c9cff",
    "accent2": "#9eb3ff",
    "danger": "#ff758c",
    "success": "#63d6a5",
}

LIGHT = {
    "bg": "#eef2fb",
    "panel": "#ffffff",
    "panel2": "#e3e9f7",
    "field": "#f8faff",
    "border": "#c6d0e4",
    "text": "#18223a",
    "muted": "#65718d",
    "accent": "#496ff2",
    "accent2": "#345ad8",
    "danger": "#c83d57",
    "success": "#158a60",
}


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def word_count(text: str) -> int:
    return len(text.split())


def open_folder(path: Path) -> None:
    path = path.resolve()
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class NoPasteText(tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<<Paste>>", lambda _event: "break")
        self.bind("<Control-v>", lambda _event: "break")
        self.bind("<Control-V>", lambda _event: "break")
        self.bind("<Shift-Insert>", lambda _event: "break")
        self.bind("<Button-3>", lambda _event: "break")


class Card(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, style="Card.TFrame", padding=kwargs.pop("padding", 18), **kwargs)


class PinDialog(simpledialog.Dialog):
    def __init__(self, parent, check: Callable[[str], bool]):
        self.check = check
        self.success = False
        super().__init__(parent, title="Teacher access")

    def body(self, master):
        ttk.Label(master, text="Enter the teacher PIN", style="DialogTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(master, text="PIN").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.entry = ttk.Entry(master, show="●", width=26)
        self.entry.grid(row=1, column=1, sticky="ew")
        master.columnconfigure(1, weight=1)
        return self.entry

    def validate(self):
        if self.check(self.entry.get()):
            self.success = True
            return True
        messagebox.showerror("Access denied", "The PIN is incorrect.", parent=self)
        self.entry.select_range(0, "end")
        return False


class LessonEditor(tk.Toplevel):
    def __init__(self, app: "DictaTypeApp", lesson: dict[str, Any] | None = None):
        super().__init__(app)
        self.app = app
        self.db = app.db
        self.lesson = lesson
        self.result_id: int | None = None
        self.title("Edit dictation" if lesson else "New dictation")
        self.geometry("860x760")
        self.minsize(760, 650)
        self.transient(app)
        self.grab_set()
        self.configure(bg=app.colors["bg"])
        self._build()
        self._load()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(5, weight=1)

        ttk.Label(outer, text="Dictation details", style="PageTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 16))

        ttk.Label(outer, text="Title").grid(row=1, column=0, sticky="w", pady=6)
        self.title_var = tk.StringVar()
        ttk.Entry(outer, textvariable=self.title_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=6)

        ttk.Label(outer, text="Language").grid(row=2, column=0, sticky="w", pady=6)
        self.language_var = tk.StringVar(value="English")
        self.language_combo = ttk.Combobox(outer, textvariable=self.language_var, values=["English", "Français"], state="readonly", width=18)
        self.language_combo.grid(row=2, column=1, sticky="ew", pady=6, padx=(0, 12))
        self.language_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_voice_values())

        ttk.Label(outer, text="Difficulty").grid(row=2, column=2, sticky="w", pady=6)
        self.difficulty_var = tk.StringVar(value="Intermediate")
        ttk.Combobox(outer, textvariable=self.difficulty_var, values=["Beginner", "Intermediate", "Advanced"], state="readonly").grid(row=2, column=3, sticky="ew", pady=6)

        ttk.Label(outer, text="Category").grid(row=3, column=0, sticky="w", pady=6)
        self.category_var = tk.StringVar()
        ttk.Entry(outer, textvariable=self.category_var).grid(row=3, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(outer, text="Voice").grid(row=3, column=2, sticky="w", pady=6)
        self.voice_var = tk.StringVar()
        self.voice_combo = ttk.Combobox(outer, textvariable=self.voice_var, state="readonly")
        self.voice_combo.grid(row=3, column=3, sticky="ew", pady=6)

        ttk.Label(outer, text="Passage").grid(row=4, column=0, sticky="nw", pady=(12, 6))
        text_frame = ttk.Frame(outer, style="Field.TFrame")
        text_frame.grid(row=5, column=0, columnspan=4, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.text = tk.Text(
            text_frame,
            wrap="word",
            undo=True,
            font=("Segoe UI", 11),
            relief="flat",
            padx=12,
            pady=12,
            bg=self.app.colors["field"],
            fg=self.app.colors["text"],
            insertbackground=self.app.colors["text"],
            selectbackground=self.app.colors["accent"],
        )
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        controls = ttk.LabelFrame(outer, text="Exercise controls", padding=14)
        controls.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(14, 8))
        for i in range(4):
            controls.columnconfigure(i, weight=1)

        ttk.Label(controls, text="Speech rate").grid(row=0, column=0, sticky="w")
        self.rate_var = tk.IntVar(value=175)
        ttk.Spinbox(controls, from_=80, to=300, increment=5, textvariable=self.rate_var, width=10).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(controls, text="Replay limit / sentence").grid(row=0, column=1, sticky="w")
        self.replay_var = tk.IntVar(value=3)
        ttk.Spinbox(controls, from_=0, to=20, textvariable=self.replay_var, width=10).grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(controls, text="Time limit (minutes, 0 = none)").grid(row=0, column=2, sticky="w")
        self.time_var = tk.IntVar(value=0)
        ttk.Spinbox(controls, from_=0, to=240, textvariable=self.time_var, width=10).grid(row=1, column=2, sticky="ew", padx=(0, 10))

        ttk.Label(controls, text="Marking mode").grid(row=0, column=3, sticky="w")
        self.marking_var = tk.StringVar(value="Balanced")
        ttk.Combobox(controls, textvariable=self.marking_var, values=["Flexible", "Balanced", "Strict"], state="readonly").grid(row=1, column=3, sticky="ew")

        self.sentence_var = tk.BooleanVar(value=True)
        self.punctuation_var = tk.BooleanVar(value=False)
        self.show_results_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Read sentence by sentence", variable=self.sentence_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Checkbutton(controls, text="Speak punctuation names", variable=self.punctuation_var).grid(row=2, column=2, sticky="w", pady=(12, 0))
        ttk.Checkbutton(controls, text="Show result to student", variable=self.show_results_var).grid(row=2, column=3, sticky="w", pady=(12, 0))

        buttons = ttk.Frame(outer)
        buttons.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Import text", style="Secondary.TButton", command=self.import_text).pack(side="left")
        ttk.Button(buttons, text="Preview voice", style="Secondary.TButton", command=self.preview).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save dictation", style="Accent.TButton", command=self.save).pack(side="right", padx=8)

    def _refresh_voice_values(self):
        language = "fr" if self.language_var.get() == "Français" else "en"
        matching = self.app.voices_for_language(language)
        values = [voice.display_name for voice in matching]
        self.voice_combo["values"] = values
        if values and self.voice_var.get() not in values:
            self.voice_var.set(values[0])
        if not values:
            self.voice_var.set("Use Windows default voice")
            self.voice_combo["values"] = ["Use Windows default voice"]

    def _load(self):
        self._refresh_voice_values()
        if not self.lesson:
            return
        self.title_var.set(self.lesson.get("title", ""))
        self.language_var.set("Français" if self.lesson.get("language") == "fr" else "English")
        self.difficulty_var.set(self.lesson.get("difficulty", "Intermediate"))
        self.category_var.set(self.lesson.get("category", ""))
        self.rate_var.set(int(self.lesson.get("rate", 175)))
        self.replay_var.set(int(self.lesson.get("replay_limit", 3)))
        self.time_var.set(int(self.lesson.get("time_limit", 0)) // 60)
        self.marking_var.set(str(self.lesson.get("marking_mode", "balanced")).title())
        self.sentence_var.set(bool(self.lesson.get("sentence_mode", 1)))
        self.punctuation_var.set(bool(self.lesson.get("speak_punctuation", 0)))
        self.show_results_var.set(bool(self.lesson.get("show_results", 1)))
        self.text.insert("1.0", self.lesson.get("text", ""))
        self._refresh_voice_values()
        voice_name = self.lesson.get("voice_name", "")
        for voice in self.app.voices:
            if voice.name == voice_name or voice.id == self.lesson.get("voice_id", ""):
                self.voice_var.set(voice.display_name)
                break

    def selected_voice(self) -> Voice | None:
        display = self.voice_var.get()
        return next((voice for voice in self.app.voices if voice.display_name == display), None)

    def import_text(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Import passage",
            filetypes=[("Text or Word document", "*.txt *.docx"), ("Text file", "*.txt"), ("Word document", "*.docx")],
        )
        if not path:
            return
        try:
            source = Path(path)
            if source.suffix.lower() == ".txt":
                content = source.read_text(encoding="utf-8-sig")
            elif source.suffix.lower() == ".docx":
                from docx import Document

                document = Document(source)
                content = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
            else:
                raise ValueError("Unsupported file format")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            if not self.title_var.get().strip():
                self.title_var.set(source.stem)
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc), parent=self)

    def preview(self):
        content = self.text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("No passage", "Enter a passage before previewing it.", parent=self)
            return
        sample = split_sentences(content)[0] if split_sentences(content) else content[:300]
        language = "fr" if self.language_var.get() == "Français" else "en"
        if self.punctuation_var.get():
            sample = verbalize_punctuation(sample, language)
        voice = self.selected_voice()
        self.app.speech.speak(
            sample,
            voice_id=voice.id if voice else "",
            rate=self.rate_var.get(),
            on_error=lambda exc: self.app.post(lambda: messagebox.showerror("Speech error", str(exc), parent=self)),
        )

    def save(self):
        content = self.text.get("1.0", "end").strip()
        if not self.title_var.get().strip():
            messagebox.showwarning("Missing title", "Enter a title for the dictation.", parent=self)
            return
        if not content:
            messagebox.showwarning("Missing passage", "Enter the text to be dictated.", parent=self)
            return
        voice = self.selected_voice()
        data = {
            "title": self.title_var.get(),
            "language": "fr" if self.language_var.get() == "Français" else "en",
            "difficulty": self.difficulty_var.get(),
            "category": self.category_var.get(),
            "text": content,
            "voice_id": voice.id if voice else "",
            "voice_name": voice.name if voice else "",
            "rate": self.rate_var.get(),
            "volume": 1.0,
            "replay_limit": self.replay_var.get(),
            "time_limit": self.time_var.get() * 60,
            "marking_mode": self.marking_var.get().lower(),
            "sentence_mode": self.sentence_var.get(),
            "speak_punctuation": self.punctuation_var.get(),
            "show_results": self.show_results_var.get(),
        }
        try:
            self.result_id = self.db.save_lesson(data, self.lesson.get("id") if self.lesson else None)
            self.app.refresh_all()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)


class ResultDialog(tk.Toplevel):
    def __init__(self, app: "DictaTypeApp", attempt: dict[str, Any]):
        super().__init__(app)
        self.app = app
        self.attempt = attempt
        self.title(f"Result · {attempt.get('student_name', '')}")
        self.geometry("920x720")
        self.minsize(780, 600)
        self.transient(app)
        self.configure(bg=app.colors["bg"])
        self._build()

    def _build(self):
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text=self.attempt.get("student_name", "Student"), style="PageTitle.TLabel").pack(side="left")
        ttk.Label(header, text=self.attempt.get("lesson_title", ""), style="Muted.TLabel").pack(side="right")

        metrics = ttk.Frame(outer)
        metrics.pack(fill="x", pady=16)
        values = [
            ("Overall", f"{self.attempt.get('overall_score', 0):.1f}%"),
            ("Words", f"{self.attempt.get('score_word', 0):.1f}%"),
            ("Characters", f"{self.attempt.get('score_char', 0):.1f}%"),
            ("Speed", f"{self.attempt.get('wpm', 0):.1f} WPM"),
            ("Time", format_duration(self.attempt.get("duration_seconds", 0))),
            ("Replays", str(self.attempt.get("replay_count", 0))),
        ]
        for index, (label, value) in enumerate(values):
            metrics.columnconfigure(index, weight=1)
            card = Card(metrics, padding=12)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 5, 0))
            ttk.Label(card, text=label, style="Muted.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="Metric.TLabel").pack(anchor="w")

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        answer_tab = ttk.Frame(notebook, padding=12)
        changes_tab = ttk.Frame(notebook, padding=12)
        details_tab = ttk.Frame(notebook, padding=12)
        notebook.add(answer_tab, text="Student answer")
        notebook.add(changes_tab, text="Corrections")
        notebook.add(details_tab, text="Analysis")

        answer_text = tk.Text(answer_tab, wrap="word", relief="flat", padx=12, pady=12, bg=self.app.colors["field"], fg=self.app.colors["text"], insertbackground=self.app.colors["text"])
        answer_text.pack(fill="both", expand=True)
        answer_text.insert("1.0", self.attempt.get("answer", ""))
        answer_text.configure(state="disabled")

        changes_text = tk.Text(changes_tab, wrap="word", relief="flat", padx=12, pady=12, bg=self.app.colors["field"], fg=self.app.colors["text"], insertbackground=self.app.colors["text"])
        changes_text.pack(fill="both", expand=True)
        details = self.attempt.get("details", {})
        changes = details.get("changes", []) if isinstance(details, dict) else []
        if changes:
            for change in changes:
                kind = change.get("kind", "change").title()
                expected = change.get("expected", "") or "∅"
                actual = change.get("actual", "") or "∅"
                changes_text.insert("end", f"{kind}: {expected}  →  {actual}\n")
        else:
            changes_text.insert("end", "No word-level corrections. Excellent work.")
        changes_text.configure(state="disabled")

        analysis = [
            ("Marking mode", details.get("mode", "balanced")),
            ("Correct words", details.get("correct_words", 0)),
            ("Substitutions", details.get("substitutions", 0)),
            ("Missing words", details.get("missing_words", 0)),
            ("Extra words", details.get("extra_words", 0)),
            ("Accent mistakes", details.get("accent_mistakes", 0)),
            ("Capitalisation mistakes", details.get("capitalization_mistakes", 0)),
            ("Punctuation mistakes", details.get("punctuation_mistakes", 0)),
        ]
        for row, (label, value) in enumerate(analysis):
            ttk.Label(details_tab, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 20), pady=6)
            ttk.Label(details_tab, text=str(value)).grid(row=row, column=1, sticky="w", pady=6)

        comment_frame = ttk.LabelFrame(outer, text="Teacher comment", padding=10)
        comment_frame.pack(fill="x", pady=(14, 0))
        self.comment_var = tk.StringVar(value=self.attempt.get("teacher_comment", ""))
        ttk.Entry(comment_frame, textvariable=self.comment_var).pack(side="left", fill="x", expand=True)
        ttk.Button(comment_frame, text="Save comment", style="Secondary.TButton", command=self.save_comment).pack(side="left", padx=(10, 0))
        ttk.Button(outer, text="Save report as HTML", style="Secondary.TButton", command=self.save_report).pack(anchor="e", pady=(12, 0))

    def save_comment(self):
        self.app.db.update_attempt_comment(int(self.attempt["id"]), self.comment_var.get())
        self.attempt["teacher_comment"] = self.comment_var.get()
        self.app.refresh_all()
        messagebox.showinfo("Saved", "The teacher comment was saved.", parent=self)

    def save_report(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".html", filetypes=[("HTML report", "*.html")], initialfile=f"DictaType_{self.attempt.get('student_name','result')}.html")
        if not path:
            return
        details = self.attempt.get("details", {})
        changes = details.get("changes", []) if isinstance(details, dict) else []
        rows = "".join(
            f"<tr><td>{html.escape(str(item.get('kind','')))}</td><td>{html.escape(str(item.get('expected','')))}</td><td>{html.escape(str(item.get('actual','')))}</td></tr>"
            for item in changes
        ) or "<tr><td colspan='3'>No word-level corrections.</td></tr>"
        document = f"""<!doctype html><meta charset='utf-8'><title>DictaType Result</title>
<style>body{{font:16px system-ui;max-width:900px;margin:40px auto;color:#1e2943}}.metrics{{display:flex;gap:12px;flex-wrap:wrap}}.box{{background:#eef2fb;padding:15px 20px;border-radius:12px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd4e5;padding:8px;text-align:left}}pre{{white-space:pre-wrap;background:#f5f7fc;padding:16px;border-radius:12px}}</style>
<h1>DictaType Result</h1><h2>{html.escape(self.attempt.get('student_name',''))}</h2><p>{html.escape(self.attempt.get('lesson_title',''))}</p>
<div class='metrics'><div class='box'><b>Overall</b><br>{self.attempt.get('overall_score',0):.1f}%</div><div class='box'><b>Word accuracy</b><br>{self.attempt.get('score_word',0):.1f}%</div><div class='box'><b>WPM</b><br>{self.attempt.get('wpm',0):.1f}</div><div class='box'><b>Time</b><br>{format_duration(self.attempt.get('duration_seconds',0))}</div></div>
<h3>Student answer</h3><pre>{html.escape(self.attempt.get('answer',''))}</pre><h3>Corrections</h3><table><tr><th>Type</th><th>Expected</th><th>Typed</th></tr>{rows}</table><h3>Teacher comment</h3><p>{html.escape(self.comment_var.get())}</p>"""
        Path(path).write_text(document, encoding="utf-8")
        messagebox.showinfo("Report saved", "The HTML report was created.", parent=self)


class StudentPage(ttk.Frame):
    def __init__(self, app: "DictaTypeApp", master):
        super().__init__(master, padding=24)
        self.app = app
        self.db = app.db
        self.current_lesson: dict[str, Any] | None = None
        self.sentences: list[str] = []
        self.sentence_index = 0
        self.play_counts: dict[int, int] = {}
        self.started_at = 0.0
        self.timer_job = None
        self.student_map: dict[str, dict[str, Any]] = {}
        self.lesson_map: dict[str, int] = {}
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="Student practice", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Listen carefully, type what you hear, then submit your answer.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 18))

        self.setup_card = Card(self)
        self.setup_card.grid(row=2, column=0, sticky="nsew")
        self.setup_card.columnconfigure(1, weight=1)
        self.setup_card.rowconfigure(5, weight=1)

        ttk.Label(self.setup_card, text="Student name").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
        self.student_var = tk.StringVar()
        self.student_combo = ttk.Combobox(self.setup_card, textvariable=self.student_var)
        self.student_combo.grid(row=0, column=1, sticky="ew", pady=6)
        self.student_combo.bind("<<ComboboxSelected>>", self._student_selected)

        ttk.Label(self.setup_card, text="Class").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
        self.class_var = tk.StringVar()
        ttk.Entry(self.setup_card, textvariable=self.class_var).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(self.setup_card, text="Dictation").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=6)
        self.lesson_var = tk.StringVar()
        self.lesson_combo = ttk.Combobox(self.setup_card, textvariable=self.lesson_var, state="readonly")
        self.lesson_combo.grid(row=2, column=1, sticky="ew", pady=6)

        self.start_button = ttk.Button(self.setup_card, text="Start exercise", style="Accent.TButton", command=self.start_exercise)
        self.start_button.grid(row=3, column=1, sticky="e", pady=(12, 6))

        separator = ttk.Separator(self.setup_card)
        separator.grid(row=4, column=0, columnspan=2, sticky="ew", pady=14)

        exercise = ttk.Frame(self.setup_card)
        exercise.grid(row=5, column=0, columnspan=2, sticky="nsew")
        exercise.columnconfigure(0, weight=1)
        exercise.rowconfigure(3, weight=1)

        top = ttk.Frame(exercise)
        top.grid(row=0, column=0, sticky="ew")
        self.exercise_title = ttk.Label(top, text="Choose a dictation to begin", style="SectionTitle.TLabel")
        self.exercise_title.pack(side="left")
        self.timer_label = ttk.Label(top, text="00:00", style="Timer.TLabel")
        self.timer_label.pack(side="right")

        self.progress_label = ttk.Label(exercise, text="", style="Muted.TLabel")
        self.progress_label.grid(row=1, column=0, sticky="w", pady=(5, 10))

        action_bar = ttk.Frame(exercise)
        action_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.listen_button = ttk.Button(action_bar, text="▶ Listen", style="Accent.TButton", command=self.play_current, state="disabled")
        self.listen_button.pack(side="left")
        self.previous_button = ttk.Button(action_bar, text="Previous", style="Secondary.TButton", command=self.previous_sentence, state="disabled")
        self.previous_button.pack(side="left", padx=(8, 0))
        self.next_button = ttk.Button(action_bar, text="Next sentence", style="Secondary.TButton", command=self.next_sentence, state="disabled")
        self.next_button.pack(side="left", padx=(8, 0))
        self.fullscreen_button = ttk.Button(action_bar, text="Full screen", style="Secondary.TButton", command=self.toggle_fullscreen, state="disabled")
        self.fullscreen_button.pack(side="right")

        answer_frame = ttk.Frame(exercise, style="Field.TFrame")
        answer_frame.grid(row=3, column=0, sticky="nsew")
        answer_frame.columnconfigure(0, weight=1)
        answer_frame.rowconfigure(0, weight=1)
        self.answer = NoPasteText(
            answer_frame,
            wrap="word",
            undo=False,
            relief="flat",
            padx=14,
            pady=14,
            font=("Segoe UI", 12),
            bg=self.app.colors["field"],
            fg=self.app.colors["text"],
            insertbackground=self.app.colors["text"],
            selectbackground=self.app.colors["accent"],
            state="disabled",
        )
        self.answer.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(answer_frame, command=self.answer.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.answer.configure(yscrollcommand=scroll.set)

        bottom = ttk.Frame(exercise)
        bottom.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.status_label = ttk.Label(bottom, text="The original passage stays hidden.", style="Muted.TLabel")
        self.status_label.pack(side="left")
        self.cancel_button = ttk.Button(bottom, text="Cancel", style="Secondary.TButton", command=self.cancel_exercise, state="disabled")
        self.cancel_button.pack(side="right")
        self.submit_button = ttk.Button(bottom, text="Submit answer", style="Accent.TButton", command=self.submit, state="disabled")
        self.submit_button.pack(side="right", padx=(0, 8))

    def refresh(self):
        students = self.db.list_students()
        self.student_map = {}
        student_values = []
        for student in students:
            label = student["name"] + (f" · {student['class_name']}" if student.get("class_name") else "")
            if label in self.student_map:
                label += f" #{student['id']}"
            self.student_map[label] = student
            student_values.append(label)
        self.student_combo["values"] = student_values

        lessons = self.db.list_lessons()
        self.lesson_map = {}
        lesson_values = []
        for lesson in lessons:
            lang = "FR" if lesson.get("language") == "fr" else "EN"
            label = f"{lesson['title']}  ·  {lang}  ·  {lesson['difficulty']}"
            if label in self.lesson_map:
                label += f"  #{lesson['id']}"
            self.lesson_map[label] = lesson["id"]
            lesson_values.append(label)
        self.lesson_combo["values"] = lesson_values
        if lesson_values and self.lesson_var.get() not in lesson_values:
            self.lesson_var.set(lesson_values[0])

    def _student_selected(self, _event=None):
        student = self.student_map.get(self.student_var.get())
        if student:
            self.class_var.set(student.get("class_name", ""))

    def start_exercise(self):
        name = self.student_var.get().split(" · ", 1)[0].strip()
        lesson_id = self.lesson_map.get(self.lesson_var.get())
        if not name:
            messagebox.showwarning("Student name", "Enter or select the student's name.", parent=self)
            return
        if not lesson_id:
            messagebox.showwarning("Dictation", "Select a dictation.", parent=self)
            return
        lesson = self.db.get_lesson(lesson_id)
        if not lesson:
            messagebox.showerror("Missing dictation", "The selected dictation could not be found.", parent=self)
            return
        self.current_lesson = lesson
        self.sentences = split_sentences(lesson["text"]) if lesson.get("sentence_mode") else [lesson["text"]]
        self.sentence_index = 0
        self.play_counts = {}
        self.started_at = time.monotonic()
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.student_combo.configure(state="disabled")
        self.lesson_combo.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.listen_button.configure(state="normal")
        self.cancel_button.configure(state="normal")
        self.submit_button.configure(state="normal")
        self.fullscreen_button.configure(state="normal")
        self.exercise_title.configure(text=lesson["title"])
        self.status_label.configure(text="Copy and paste are disabled during the exercise.")
        self._update_progress()
        self._tick()
        self.after(350, self.play_current)
        self.answer.focus_set()

    def current_voice(self) -> Voice | None:
        if not self.current_lesson:
            return None
        voice_id = self.current_lesson.get("voice_id", "")
        return next((voice for voice in self.app.voices if voice.id == voice_id), None)

    def play_current(self):
        if not self.current_lesson or not self.sentences:
            return
        limit = int(self.current_lesson.get("replay_limit", 3))
        count = self.play_counts.get(self.sentence_index, 0)
        # One initial playback plus the configured number of replays.
        if limit > 0 and count >= limit + 1:
            self.status_label.configure(text="The replay limit for this sentence has been reached.")
            return
        text = self.sentences[self.sentence_index]
        if self.current_lesson.get("speak_punctuation"):
            text = verbalize_punctuation(text, self.current_lesson.get("language", "en"))
        self.play_counts[self.sentence_index] = count + 1
        self.status_label.configure(text="Playing audio…")
        voice = self.current_voice()
        self.app.speech.speak(
            text,
            voice_id=voice.id if voice else self.current_lesson.get("voice_id", ""),
            rate=int(self.current_lesson.get("rate", 175)),
            volume=float(self.current_lesson.get("volume", 1.0)),
            on_done=lambda: self.app.post(lambda: self.status_label.configure(text="Audio finished. Continue typing.")),
            on_error=lambda exc: self.app.post(lambda: messagebox.showerror("Speech error", str(exc), parent=self)),
        )
        self._update_progress()

    def previous_sentence(self):
        if self.sentence_index > 0:
            self.sentence_index -= 1
            self._update_progress()

    def next_sentence(self):
        if self.sentence_index < len(self.sentences) - 1:
            self.sentence_index += 1
            self._update_progress()
            self.play_current()
        else:
            self.status_label.configure(text="This is the final sentence. Review your answer and submit.")

    def _update_progress(self):
        total = max(1, len(self.sentences))
        current = self.sentence_index + 1
        count = self.play_counts.get(self.sentence_index, 0)
        replay_limit = int(self.current_lesson.get("replay_limit", 3)) if self.current_lesson else 0
        replay_text = "Unlimited" if replay_limit == 0 else f"{max(0, count - 1)}/{replay_limit} replays"
        self.progress_label.configure(text=f"Sentence {current} of {total}  ·  {replay_text}")
        self.previous_button.configure(state="normal" if self.sentence_index > 0 else "disabled")
        self.next_button.configure(state="normal" if self.sentence_index < total - 1 else "disabled")

    def _tick(self):
        if not self.current_lesson:
            return
        elapsed = int(time.monotonic() - self.started_at)
        limit = int(self.current_lesson.get("time_limit", 0))
        if limit > 0:
            remaining = max(0, limit - elapsed)
            self.timer_label.configure(text=format_duration(remaining))
            if remaining <= 0:
                self.status_label.configure(text="Time is up. Your answer has been submitted automatically.")
                self.submit(auto=True)
                return
        else:
            self.timer_label.configure(text=format_duration(elapsed))
        self.timer_job = self.after(1000, self._tick)

    def total_plays(self) -> int:
        return sum(self.play_counts.values())

    def submit(self, auto: bool = False):
        if not self.current_lesson:
            return
        answer = self.answer.get("1.0", "end").strip()
        if not answer and not auto:
            if not messagebox.askyesno("Empty answer", "Submit an empty answer?", parent=self):
                return
        elapsed = max(1, int(time.monotonic() - self.started_at))
        result = score_text(self.current_lesson["text"], answer, self.current_lesson.get("marking_mode", "balanced"))
        wpm = calculate_wpm(answer, elapsed)
        student_label = self.student_var.get()
        student = self.student_map.get(student_label)
        student_name = student["name"] if student else student_label.split(" · ", 1)[0].strip()
        attempt_id = self.db.save_attempt(
            {
                "student_id": student.get("id") if student else None,
                "student_name": student_name or "Anonymous",
                "class_name": self.class_var.get(),
                "lesson_id": self.current_lesson["id"],
                "lesson_title": self.current_lesson["title"],
                "answer": answer,
                "score_word": result.word_accuracy,
                "score_char": result.character_accuracy,
                "overall_score": result.overall_score,
                "wpm": wpm,
                "duration_seconds": elapsed,
                "replay_count": self.total_plays(),
                "details": result.to_dict(),
                "source": "desktop",
            }
        )
        show = bool(self.current_lesson.get("show_results", 1))
        self._finish_exercise()
        self.app.refresh_all()
        if show:
            attempt = self.db.get_attempt(attempt_id)
            if attempt:
                ResultDialog(self.app, attempt)
        else:
            messagebox.showinfo("Answer submitted", "The answer was saved for the teacher.", parent=self)

    def cancel_exercise(self):
        if self.current_lesson and not messagebox.askyesno("Cancel exercise", "Discard this attempt and return to the start screen?", parent=self):
            return
        self._finish_exercise()

    def _finish_exercise(self):
        self.app.speech.stop()
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
        self.timer_job = None
        self.current_lesson = None
        self.sentences = []
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.configure(state="disabled")
        self.student_combo.configure(state="normal")
        self.lesson_combo.configure(state="readonly")
        self.start_button.configure(state="normal")
        for widget in [self.listen_button, self.previous_button, self.next_button, self.cancel_button, self.submit_button, self.fullscreen_button]:
            widget.configure(state="disabled")
        self.exercise_title.configure(text="Choose a dictation to begin")
        self.progress_label.configure(text="")
        self.timer_label.configure(text="00:00")
        self.status_label.configure(text="The original passage stays hidden.")
        self.app.attributes("-fullscreen", False)

    def toggle_fullscreen(self):
        self.app.attributes("-fullscreen", not bool(self.app.attributes("-fullscreen")))


class TeacherPage(ttk.Frame):
    def __init__(self, app: "DictaTypeApp", master):
        super().__init__(master, padding=24)
        self.app = app
        self.db = app.db
        self._build()

    def _build(self):
        ttk.Label(self, text="Teacher dashboard", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text="Manage dictations, students and assessment results.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self._build_lessons_tab()
        self._build_students_tab()
        self._build_results_tab()

    def _build_lessons_tab(self):
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="Dictations")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(bar, text="New dictation", style="Accent.TButton", command=lambda: LessonEditor(self.app)).pack(side="left")
        ttk.Button(bar, text="Edit", style="Secondary.TButton", command=self.edit_lesson).pack(side="left", padx=6)
        ttk.Button(bar, text="Duplicate", style="Secondary.TButton", command=self.duplicate_lesson).pack(side="left")
        ttk.Button(bar, text="Delete", style="Danger.TButton", command=self.delete_lesson).pack(side="left", padx=6)
        ttk.Button(bar, text="Import JSON", style="Secondary.TButton", command=self.import_lessons_json).pack(side="right")
        ttk.Button(bar, text="Export JSON", style="Secondary.TButton", command=self.export_lessons_json).pack(side="right", padx=6)
        columns = ("title", "lang", "category", "difficulty", "words", "updated")
        self.lessons_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        headings = {"title": "Title", "lang": "Language", "category": "Category", "difficulty": "Difficulty", "words": "Words", "updated": "Updated"}
        widths = {"title": 290, "lang": 80, "category": 130, "difficulty": 110, "words": 70, "updated": 150}
        for column in columns:
            self.lessons_tree.heading(column, text=headings[column])
            self.lessons_tree.column(column, width=widths[column], anchor="w")
        self.lessons_tree.grid(row=1, column=0, sticky="nsew")
        self.lessons_tree.bind("<Double-1>", lambda _e: self.edit_lesson())
        scroll = ttk.Scrollbar(tab, command=self.lessons_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.lessons_tree.configure(yscrollcommand=scroll.set)

    def _build_students_tab(self):
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="Students")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(bar, text="Add student", style="Accent.TButton", command=self.add_student).pack(side="left")
        ttk.Button(bar, text="Edit", style="Secondary.TButton", command=self.edit_student).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete", style="Danger.TButton", command=self.delete_student).pack(side="left")
        columns = ("name", "class", "identifier", "created")
        self.students_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for column, label, width in [("name", "Name", 260), ("class", "Class", 180), ("identifier", "Identifier", 180), ("created", "Added", 180)]:
            self.students_tree.heading(column, text=label)
            self.students_tree.column(column, width=width, anchor="w")
        self.students_tree.grid(row=1, column=0, sticky="nsew")
        self.students_tree.bind("<Double-1>", lambda _e: self.edit_student())
        scroll = ttk.Scrollbar(tab, command=self.students_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.students_tree.configure(yscrollcommand=scroll.set)

    def _build_results_tab(self):
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="Results")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        filters = ttk.Frame(tab)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(filters, text="Search").pack(side="left")
        self.result_search_var = tk.StringVar()
        entry = ttk.Entry(filters, textvariable=self.result_search_var, width=35)
        entry.pack(side="left", padx=(8, 14))
        entry.bind("<KeyRelease>", lambda _e: self.refresh_results())
        self.result_count_label = ttk.Label(filters, text="", style="Muted.TLabel")
        self.result_count_label.pack(side="right")
        bar = ttk.Frame(tab)
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(bar, text="View result", style="Accent.TButton", command=self.view_result).pack(side="left")
        ttk.Button(bar, text="Delete", style="Danger.TButton", command=self.delete_result).pack(side="left", padx=6)
        ttk.Button(bar, text="Export Excel", style="Secondary.TButton", command=self.export_results_xlsx).pack(side="right")
        ttk.Button(bar, text="Export CSV", style="Secondary.TButton", command=self.export_results_csv).pack(side="right", padx=6)
        columns = ("date", "student", "class", "lesson", "score", "wpm", "source")
        self.results_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for column, label, width in [("date", "Date", 155), ("student", "Student", 170), ("class", "Class", 100), ("lesson", "Dictation", 240), ("score", "Score", 85), ("wpm", "WPM", 70), ("source", "Source", 90)]:
            self.results_tree.heading(column, text=label)
            self.results_tree.column(column, width=width, anchor="w")
        self.results_tree.grid(row=2, column=0, sticky="nsew")
        self.results_tree.bind("<Double-1>", lambda _e: self.view_result())
        scroll = ttk.Scrollbar(tab, command=self.results_tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.results_tree.configure(yscrollcommand=scroll.set)

    def refresh(self):
        self.refresh_lessons()
        self.refresh_students()
        self.refresh_results()

    def refresh_lessons(self):
        self.lessons_tree.delete(*self.lessons_tree.get_children())
        for lesson in self.db.list_lessons():
            updated = lesson.get("updated_at", "").replace("T", " ")[:16]
            self.lessons_tree.insert("", "end", iid=str(lesson["id"]), values=(lesson["title"], "Français" if lesson["language"] == "fr" else "English", lesson.get("category", ""), lesson.get("difficulty", ""), word_count(lesson.get("text", "")), updated))

    def selected_id(self, tree: ttk.Treeview) -> int | None:
        selection = tree.selection()
        return int(selection[0]) if selection else None

    def edit_lesson(self):
        lesson_id = self.selected_id(self.lessons_tree)
        if lesson_id is None:
            messagebox.showinfo("Select a dictation", "Select a dictation to edit.", parent=self)
            return
        lesson = self.db.get_lesson(lesson_id)
        if lesson:
            LessonEditor(self.app, lesson)

    def duplicate_lesson(self):
        lesson_id = self.selected_id(self.lessons_tree)
        if lesson_id is None:
            return
        self.db.duplicate_lesson(lesson_id)
        self.app.refresh_all()

    def delete_lesson(self):
        lesson_id = self.selected_id(self.lessons_tree)
        if lesson_id is None:
            return
        if messagebox.askyesno("Delete dictation", "Delete this dictation? Existing results will remain available.", parent=self):
            self.db.delete_lesson(lesson_id)
            self.app.refresh_all()

    def export_lessons_json(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("DictaType lessons", "*.json")], initialfile="dictatype_lessons.json")
        if not path:
            return
        payload = {"format": "DictaType lessons", "version": 1, "lessons": self.db.export_lessons()}
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Export complete", "The lessons were exported.", parent=self)

    def import_lessons_json(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("DictaType lessons", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            lessons = payload.get("lessons", payload if isinstance(payload, list) else [])
            count = self.db.import_lessons(lessons)
            self.app.refresh_all()
            messagebox.showinfo("Import complete", f"Imported {count} dictation(s).", parent=self)
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc), parent=self)

    def refresh_students(self):
        self.students_tree.delete(*self.students_tree.get_children())
        for student in self.db.list_students():
            created = student.get("created_at", "").replace("T", " ")[:16]
            self.students_tree.insert("", "end", iid=str(student["id"]), values=(student["name"], student.get("class_name", ""), student.get("identifier", ""), created))

    def student_form(self, student: dict[str, Any] | None = None):
        dialog = tk.Toplevel(self.app)
        dialog.title("Edit student" if student else "Add student")
        dialog.geometry("460x280")
        dialog.transient(self.app)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        name_var = tk.StringVar(value=student.get("name", "") if student else "")
        class_var = tk.StringVar(value=student.get("class_name", "") if student else "")
        id_var = tk.StringVar(value=student.get("identifier", "") if student else "")
        for row, (label, variable) in enumerate([("Name", name_var), ("Class", class_var), ("Identifier", id_var)]):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=8)
            ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=8)

        def save():
            if not name_var.get().strip():
                messagebox.showwarning("Missing name", "Enter the student's name.", parent=dialog)
                return
            self.db.save_student(name_var.get(), class_var.get(), id_var.get(), student.get("id") if student else None)
            dialog.destroy()
            self.app.refresh_all()

        ttk.Button(frame, text="Save", style="Accent.TButton", command=save).grid(row=4, column=1, sticky="e", pady=(18, 0))

    def add_student(self):
        self.student_form()

    def edit_student(self):
        student_id = self.selected_id(self.students_tree)
        if student_id is None:
            return
        student = next((item for item in self.db.list_students() if item["id"] == student_id), None)
        if student:
            self.student_form(student)

    def delete_student(self):
        student_id = self.selected_id(self.students_tree)
        if student_id is None:
            return
        if messagebox.askyesno("Delete student", "Delete this student? Their previous results will remain available.", parent=self):
            self.db.delete_student(student_id)
            self.app.refresh_all()

    def filtered_attempts(self):
        query = self.result_search_var.get().strip().casefold()
        attempts = self.db.list_attempts()
        if not query:
            return attempts
        return [item for item in attempts if query in " ".join([item.get("student_name", ""), item.get("class_name", ""), item.get("lesson_title", ""), item.get("source", "")]).casefold()]

    def refresh_results(self):
        self.results_tree.delete(*self.results_tree.get_children())
        attempts = self.filtered_attempts()
        for attempt in attempts:
            created = attempt.get("created_at", "").replace("T", " ")[:16]
            self.results_tree.insert("", "end", iid=str(attempt["id"]), values=(created, attempt.get("student_name", ""), attempt.get("class_name", ""), attempt.get("lesson_title", ""), f"{attempt.get('overall_score', 0):.1f}%", f"{attempt.get('wpm', 0):.1f}", attempt.get("source", "")))
        self.result_count_label.configure(text=f"{len(attempts)} result(s)")

    def view_result(self):
        attempt_id = self.selected_id(self.results_tree)
        if attempt_id is None:
            return
        attempt = self.db.get_attempt(attempt_id)
        if attempt:
            ResultDialog(self.app, attempt)

    def delete_result(self):
        attempt_id = self.selected_id(self.results_tree)
        if attempt_id is not None and messagebox.askyesno("Delete result", "Permanently delete this result?", parent=self):
            self.db.delete_attempt(attempt_id)
            self.app.refresh_all()

    def export_results_csv(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV file", "*.csv")], initialfile="dictatype_results.csv")
        if not path:
            return
        rows = self.filtered_attempts()
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Student", "Class", "Dictation", "Overall Score", "Word Accuracy", "Character Accuracy", "WPM", "Duration Seconds", "Replays", "Source", "Teacher Comment"])
            for item in rows:
                writer.writerow([item.get("created_at"), item.get("student_name"), item.get("class_name"), item.get("lesson_title"), item.get("overall_score"), item.get("score_word"), item.get("score_char"), item.get("wpm"), item.get("duration_seconds"), item.get("replay_count"), item.get("source"), item.get("teacher_comment")])
        messagebox.showinfo("Export complete", "The CSV file was created.", parent=self)

    def export_results_xlsx(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")], initialfile="dictatype_results.xlsx")
        if not path:
            return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.utils import get_column_letter

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Results"
            headers = ["Date", "Student", "Class", "Dictation", "Overall Score (%)", "Word Accuracy (%)", "Character Accuracy (%)", "WPM", "Duration (seconds)", "Replays", "Source", "Teacher Comment"]
            sheet.append(headers)
            for item in self.filtered_attempts():
                sheet.append([item.get("created_at"), item.get("student_name"), item.get("class_name"), item.get("lesson_title"), item.get("overall_score"), item.get("score_word"), item.get("score_char"), item.get("wpm"), item.get("duration_seconds"), item.get("replay_count"), item.get("source"), item.get("teacher_comment")])
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="496FF2")
                cell.alignment = Alignment(horizontal="center")
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            widths = [22, 22, 15, 35, 18, 18, 20, 10, 20, 10, 12, 35]
            for index, width in enumerate(widths, start=1):
                sheet.column_dimensions[get_column_letter(index)].width = width
            workbook.save(path)
            messagebox.showinfo("Export complete", "The Excel workbook was created.", parent=self)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)


class ClassroomPage(ttk.Frame):
    def __init__(self, app: "DictaTypeApp", master):
        super().__init__(master, padding=24)
        self.app = app
        self.db = app.db
        self.lesson_map: dict[str, int] = {}
        self._build()

    def _build(self):
        ttk.Label(self, text="Local classroom", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text="Students join from a browser on the same Wi-Fi or local network. No internet account is required.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))
        card = Card(self)
        card.pack(fill="x")
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="Dictation").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=7)
        self.lesson_var = tk.StringVar()
        self.lesson_combo = ttk.Combobox(card, textvariable=self.lesson_var, state="readonly")
        self.lesson_combo.grid(row=0, column=1, sticky="ew", pady=7)
        ttk.Label(card, text="Starting port").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=7)
        self.port_var = tk.IntVar(value=8765)
        ttk.Spinbox(card, from_=1024, to=65535, textvariable=self.port_var).grid(row=1, column=1, sticky="w", pady=7)
        buttons = ttk.Frame(card)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(buttons, text="Start classroom", style="Accent.TButton", command=self.start_server)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Stop", style="Danger.TButton", command=self.stop_server, state="disabled")
        self.stop_button.pack(side="left", padx=8)

        session_card = Card(self)
        session_card.pack(fill="x", pady=14)
        session_card.columnconfigure(1, weight=1)
        ttk.Label(session_card, text="Student address", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=5)
        self.url_var = tk.StringVar(value="Classroom is not running")
        ttk.Entry(session_card, textvariable=self.url_var, state="readonly").grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Button(session_card, text="Open", style="Secondary.TButton", command=lambda: webbrowser.open(self.url_var.get())).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(session_card, text="Session code", style="Muted.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=5)
        self.code_var = tk.StringVar(value="------")
        ttk.Label(session_card, textvariable=self.code_var, style="Code.TLabel").grid(row=1, column=1, sticky="w", pady=5)
        ttk.Button(session_card, text="Copy details", style="Secondary.TButton", command=self.copy_details).grid(row=1, column=2, padx=(8, 0))

        ttk.Label(self, text="Recent classroom submissions", style="SectionTitle.TLabel").pack(anchor="w", pady=(10, 8))
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("date", "student", "class", "lesson", "score")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, title, width in [("date", "Date", 160), ("student", "Student", 190), ("class", "Class", 130), ("lesson", "Dictation", 280), ("score", "Score", 90)]:
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.view_submission)
        scroll = ttk.Scrollbar(frame, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

    def refresh(self):
        lessons = self.db.list_lessons()
        self.lesson_map = {}
        values = []
        for lesson in lessons:
            label = f"{lesson['title']} · {'FR' if lesson['language'] == 'fr' else 'EN'}"
            self.lesson_map[label] = lesson["id"]
            values.append(label)
        self.lesson_combo["values"] = values
        if values and self.lesson_var.get() not in values:
            self.lesson_var.set(values[0])
        self.tree.delete(*self.tree.get_children())
        for attempt in [item for item in self.db.list_attempts(200) if item.get("source") == "classroom"]:
            self.tree.insert("", "end", iid=str(attempt["id"]), values=(attempt.get("created_at", "").replace("T", " ")[:16], attempt.get("student_name", ""), attempt.get("class_name", ""), attempt.get("lesson_title", ""), f"{attempt.get('overall_score',0):.1f}%"))

    def start_server(self):
        lesson_id = self.lesson_map.get(self.lesson_var.get())
        lesson = self.db.get_lesson(lesson_id) if lesson_id else None
        if not lesson:
            messagebox.showwarning("Select a dictation", "Choose the dictation to distribute.", parent=self)
            return
        try:
            url, code = self.app.classroom_server.start(lesson, self.port_var.get())
            self.url_var.set(url)
            self.code_var.set(code)
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.lesson_combo.configure(state="disabled")
            messagebox.showinfo("Classroom started", f"Students can open:\n{url}\n\nSession code: {code}", parent=self)
        except Exception as exc:
            messagebox.showerror("Could not start classroom", str(exc), parent=self)

    def stop_server(self):
        self.app.classroom_server.stop()
        self.url_var.set("Classroom is not running")
        self.code_var.set("------")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.lesson_combo.configure(state="readonly")

    def copy_details(self):
        if not self.app.classroom_server.running:
            return
        text = f"DictaType classroom\nAddress: {self.url_var.get()}\nSession code: {self.code_var.get()}"
        self.clipboard_clear()
        self.clipboard_append(text)

    def view_submission(self, _event=None):
        selection = self.tree.selection()
        if selection:
            attempt = self.db.get_attempt(int(selection[0]))
            if attempt:
                ResultDialog(self.app, attempt)


class SettingsPage(ttk.Frame):
    def __init__(self, app: "DictaTypeApp", master):
        super().__init__(master, padding=24)
        self.app = app
        self.db = app.db
        self._build()

    def _build(self):
        ttk.Label(self, text="Settings and maintenance", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text="Control appearance, security and local data backups.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))

        appearance = Card(self)
        appearance.pack(fill="x", pady=(0, 12))
        appearance.columnconfigure(1, weight=1)
        ttk.Label(appearance, text="Appearance", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(appearance, text="Theme").grid(row=1, column=0, sticky="w", padx=(0, 20))
        self.theme_var = tk.StringVar(value=self.db.get_setting("theme", "dark").title())
        ttk.Combobox(appearance, textvariable=self.theme_var, values=["Dark", "Light"], state="readonly", width=16).grid(row=1, column=1, sticky="w")
        ttk.Button(appearance, text="Apply theme", style="Secondary.TButton", command=self.apply_theme).grid(row=1, column=2, padx=(12, 0))

        security = Card(self)
        security.pack(fill="x", pady=(0, 12))
        ttk.Label(security, text="Teacher security", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(security, text="The teacher dashboard, classroom controls and settings are protected by a local PIN.", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(security, text="Change teacher PIN", style="Secondary.TButton", command=self.change_pin).pack(anchor="w", pady=(12, 0))

        data = Card(self)
        data.pack(fill="x", pady=(0, 12))
        ttk.Label(data, text="Local data", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(data, text=f"Data folder: {app_data_dir()}", style="Muted.TLabel").pack(anchor="w")
        buttons = ttk.Frame(data)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Back up database", style="Accent.TButton", command=self.backup).pack(side="left")
        ttk.Button(buttons, text="Restore database", style="Secondary.TButton", command=self.restore).pack(side="left", padx=8)
        ttk.Button(buttons, text="Open data folder", style="Secondary.TButton", command=lambda: open_folder(app_data_dir())).pack(side="left")

        voices = Card(self)
        voices.pack(fill="x")
        ttk.Label(voices, text="System voices", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        self.voice_label = ttk.Label(voices, text="", style="Muted.TLabel")
        self.voice_label.pack(anchor="w")
        ttk.Button(voices, text="Refresh installed voices", style="Secondary.TButton", command=self.refresh_voices).pack(anchor="w", pady=(12, 0))
        self.refresh()

    def refresh(self):
        english = len(self.app.voices_for_language("en"))
        french = len(self.app.voices_for_language("fr"))
        self.voice_label.configure(text=f"Detected {len(self.app.voices)} system voice(s): {english} English, {french} French or French-compatible.")

    def apply_theme(self):
        value = self.theme_var.get().lower()
        self.db.set_setting("theme", value)
        messagebox.showinfo("Theme saved", "Restart DictaType to apply the theme everywhere.", parent=self)

    def change_pin(self):
        current = simpledialog.askstring("Current PIN", "Enter the current teacher PIN:", show="●", parent=self)
        if current is None:
            return
        if not self.db.check_pin(current):
            messagebox.showerror("Incorrect PIN", "The current PIN is incorrect.", parent=self)
            return
        new = simpledialog.askstring("New PIN", "Enter a new PIN with at least 4 characters:", show="●", parent=self)
        if not new or len(new) < 4:
            messagebox.showwarning("Invalid PIN", "The PIN must contain at least 4 characters.", parent=self)
            return
        confirm = simpledialog.askstring("Confirm PIN", "Enter the new PIN again:", show="●", parent=self)
        if new != confirm:
            messagebox.showerror("PIN mismatch", "The PINs do not match.", parent=self)
            return
        self.db.set_pin(new)
        messagebox.showinfo("PIN changed", "The teacher PIN was updated.", parent=self)

    def backup(self):
        default = f"DictaType_backup_{datetime.now():%Y-%m-%d}.db"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".db", filetypes=[("DictaType database", "*.db")], initialfile=default)
        if not path:
            return
        try:
            self.db.backup(Path(path))
            messagebox.showinfo("Backup complete", "The database backup was created.", parent=self)
        except Exception as exc:
            messagebox.showerror("Backup failed", str(exc), parent=self)

    def restore(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("DictaType database", "*.db"), ("All files", "*.*")])
        if not path:
            return
        if not messagebox.askyesno("Restore database", "This replaces the current local database. Continue?", parent=self):
            return
        try:
            self.app.classroom_server.stop()
            self.db.restore(Path(path))
            self.app.refresh_all()
            messagebox.showinfo("Restore complete", "The database was restored.", parent=self)
        except Exception as exc:
            messagebox.showerror("Restore failed", str(exc), parent=self)

    def refresh_voices(self):
        self.app.refresh_voices()
        self.refresh()
        messagebox.showinfo("Voices refreshed", "Installed system voices were scanned again.", parent=self)


class DictaTypeApp(tk.Tk):
    def __init__(self, db_path: Path | None = None):
        super().__init__()
        self.db = Database(db_path)
        self.colors = DARK if self.db.get_setting("theme", "dark") == "dark" else LIGHT
        self.speech = SpeechEngine()
        self.voices: list[Voice] = list_voices()
        self.teacher_authenticated = False
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._closing = False
        self.classroom_server = ClassroomServer(self.db, on_submission=lambda: self.post(self.refresh_all))
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry(self.db.get_setting("window_geometry", "1100x720"))
        self.minsize(980, 650)
        self.configure(bg=self.colors["bg"])
        self.option_add("*Font", ("Segoe UI", 10))
        self._configure_styles()
        self._build_shell()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", lambda _e: self.attributes("-fullscreen", False))
        self.show_page("student")
        self.refresh_all()
        self.after(60, self._drain_ui_queue)
        self.after(300, self.first_run_notice)


    def post(self, callback: Callable[[], None]) -> None:
        if not self._closing:
            self._ui_queue.put(callback)

    def _drain_ui_queue(self) -> None:
        if self._closing:
            return
        for _ in range(100):
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                pass
        self.after(60, self._drain_ui_queue)

    def _configure_styles(self):
        c = self.colors
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=c["bg"], foreground=c["text"], fieldbackground=c["field"], bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"])
        style.configure("TFrame", background=c["bg"])
        style.configure("Card.TFrame", background=c["panel"], borderwidth=1, relief="solid")
        style.configure("Field.TFrame", background=c["field"], borderwidth=1, relief="solid")
        style.configure("TLabel", background=c["bg"], foreground=c["text"])
        style.configure("PageTitle.TLabel", font=("Segoe UI Semibold", 24), background=c["bg"], foreground=c["text"])
        style.configure("SectionTitle.TLabel", font=("Segoe UI Semibold", 14), background=c["bg"], foreground=c["text"])
        style.configure("DialogTitle.TLabel", font=("Segoe UI Semibold", 14))
        style.configure("Muted.TLabel", foreground=c["muted"], background=c["bg"])
        style.configure("Metric.TLabel", font=("Segoe UI Semibold", 16), background=c["panel"], foreground=c["text"])
        style.configure("Timer.TLabel", font=("Consolas", 16, "bold"), foreground=c["accent2"], background=c["bg"])
        style.configure("Code.TLabel", font=("Consolas", 28, "bold"), foreground=c["accent2"], background=c["panel"])
        style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"], insertcolor=c["text"], borderwidth=1, padding=8)
        style.configure("TCombobox", fieldbackground=c["field"], foreground=c["text"], arrowcolor=c["text"], padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", c["field"])], foreground=[("readonly", c["text"])])
        style.configure("TSpinbox", fieldbackground=c["field"], foreground=c["text"], arrowcolor=c["text"], padding=7)
        style.configure("TButton", padding=(13, 8), borderwidth=0, font=("Segoe UI Semibold", 10))
        style.configure("Accent.TButton", background=c["accent"], foreground="#081020")
        style.map("Accent.TButton", background=[("active", c["accent2"]), ("disabled", c["panel2"])])
        style.configure("Secondary.TButton", background=c["panel2"], foreground=c["text"])
        style.map("Secondary.TButton", background=[("active", c["border"])])
        style.configure("Danger.TButton", background=c["danger"], foreground="#21040b")
        style.map("Danger.TButton", background=[("active", c["danger"])])
        style.configure("Sidebar.TFrame", background=c["panel"])
        style.configure("Sidebar.TButton", background=c["panel"], foreground=c["muted"], anchor="w", padding=(16, 12))
        style.map("Sidebar.TButton", background=[("active", c["panel2"]), ("selected", c["panel2"])], foreground=[("active", c["text"]), ("selected", c["text"])])
        style.configure("Treeview", background=c["field"], fieldbackground=c["field"], foreground=c["text"], rowheight=30, bordercolor=c["border"])
        style.map("Treeview", background=[("selected", c["accent"])], foreground=[("selected", "#071020")])
        style.configure("Treeview.Heading", background=c["panel2"], foreground=c["text"], padding=8, font=("Segoe UI Semibold", 9))
        style.configure("TNotebook", background=c["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=c["panel"], foreground=c["muted"], padding=(16, 9))
        style.map("TNotebook.Tab", background=[("selected", c["accent"])], foreground=[("selected", "#071020")])
        style.configure("TLabelframe", background=c["bg"], foreground=c["text"], bordercolor=c["border"])
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["text"], font=("Segoe UI Semibold", 10))
        style.configure("TCheckbutton", background=c["bg"], foreground=c["text"])

    def _build_shell(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", padding=(12, 18))
        sidebar.grid(row=0, column=0, sticky="ns")
        ttk.Label(sidebar, text="DT", font=("Segoe UI Semibold", 25), foreground=self.colors["accent"], background=self.colors["panel"]).pack(anchor="w", padx=10)
        ttk.Label(sidebar, text="DictaType", font=("Segoe UI Semibold", 12), foreground=self.colors["text"], background=self.colors["panel"]).pack(anchor="w", padx=10, pady=(0, 24))
        self.nav_buttons: dict[str, ttk.Button] = {}
        nav = [
            ("student", "⌨  Student practice", False),
            ("teacher", "▦  Teacher dashboard", True),
            ("classroom", "◉  Local classroom", True),
            ("settings", "⚙  Settings", True),
        ]
        for key, label, protected in nav:
            button = ttk.Button(sidebar, text=label, style="Sidebar.TButton", width=24, command=lambda k=key, p=protected: self.navigate(k, p))
            button.pack(fill="x", pady=2)
            self.nav_buttons[key] = button
        ttk.Label(sidebar, text=f"Open source · v{APP_VERSION}", foreground=self.colors["muted"], background=self.colors["panel"]).pack(side="bottom", anchor="w", padx=10, pady=8)

        self.content = ttk.Frame(self)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.pages = {
            "student": StudentPage(self, self.content),
            "teacher": TeacherPage(self, self.content),
            "classroom": ClassroomPage(self, self.content),
            "settings": SettingsPage(self, self.content),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def navigate(self, key: str, protected: bool = False):
        if protected and not self.teacher_authenticated:
            dialog = PinDialog(self, self.db.check_pin)
            if not dialog.success:
                return
            self.teacher_authenticated = True
        self.show_page(key)

    def show_page(self, key: str):
        page = self.pages[key]
        page.tkraise()
        for name, button in self.nav_buttons.items():
            button.state(["selected"] if name == key else ["!selected"])
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def refresh_all(self):
        for page in self.pages.values():
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:
                    pass

    def voices_for_language(self, language: str) -> list[Voice]:
        language = language.casefold()
        matches = []
        for voice in self.voices:
            haystack = " ".join([voice.id, voice.name, *voice.languages]).casefold()
            if language == "fr" and any(token in haystack for token in ["fr-", "fr_", "french", "français", "hortense", "denise"]):
                matches.append(voice)
            elif language == "en" and any(token in haystack for token in ["en-", "en_", "english", "zira", "david", "mark", "hazel"]):
                matches.append(voice)
        return matches or self.voices

    def refresh_voices(self):
        self.voices = list_voices()
        self.refresh_all()

    def first_run_notice(self):
        if self.db.get_setting("first_run", "1") == "1":
            messagebox.showinfo(
                "Welcome to DictaType",
                "The default teacher PIN is 1234.\n\nOpen Settings after signing in to change it. DictaType stores all lessons and results locally on this computer.",
                parent=self,
            )
            self.db.set_setting("first_run", "0")

    def on_close(self):
        self._closing = True
        try:
            self.db.set_setting("window_geometry", self.geometry())
        except Exception:
            pass
        self.speech.stop()
        self.classroom_server.stop()
        self.destroy()
