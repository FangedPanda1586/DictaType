from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Callable

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    languages: tuple[str, ...]

    @property
    def display_name(self) -> str:
        language_text = ", ".join(self.languages) if self.languages else "System"
        return f"{self.name} · {language_text}"


def _decode_language(value) -> str:
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            value = str(value)
    value = str(value).replace("\x05", "").replace("_", "-")
    return value or "system"


def list_voices() -> list[Voice]:
    if pyttsx3 is None:
        return []
    try:
        engine = pyttsx3.init()
        voices = []
        for raw in engine.getProperty("voices") or []:
            languages = tuple(_decode_language(item) for item in (getattr(raw, "languages", []) or []))
            voices.append(
                Voice(
                    id=str(getattr(raw, "id", "")),
                    name=str(getattr(raw, "name", "System voice")),
                    languages=languages,
                )
            )
        engine.stop()
        return voices
    except Exception:
        return []


def verbalize_punctuation(text: str, language: str) -> str:
    names = {
        "en": {
            ".": " full stop ",
            ",": " comma ",
            ";": " semicolon ",
            ":": " colon ",
            "?": " question mark ",
            "!": " exclamation mark ",
            "-": " hyphen ",
            "(": " open parenthesis ",
            ")": " close parenthesis ",
            '"': " quotation mark ",
        },
        "fr": {
            ".": " point ",
            ",": " virgule ",
            ";": " point-virgule ",
            ":": " deux-points ",
            "?": " point d'interrogation ",
            "!": " point d'exclamation ",
            "-": " trait d'union ",
            "(": " parenthèse ouvrante ",
            ")": " parenthèse fermante ",
            '"': " guillemet ",
        },
    }
    mapping = names.get(language, names["en"])
    for symbol, spoken in mapping.items():
        text = text.replace(symbol, spoken)
    return re.sub(r"\s+", " ", text).strip()


class SpeechEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._engine = None
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return pyttsx3 is not None

    def speak(
        self,
        text: str,
        voice_id: str = "",
        rate: int = 175,
        volume: float = 1.0,
        on_done: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.stop()

        def worker() -> None:
            try:
                if pyttsx3 is None:
                    raise RuntimeError("Text-to-speech support is not installed.")
                engine = pyttsx3.init()
                with self._lock:
                    self._engine = engine
                if voice_id:
                    engine.setProperty("voice", voice_id)
                engine.setProperty("rate", int(rate))
                engine.setProperty("volume", max(0.0, min(1.0, float(volume))))
                engine.say(text)
                engine.runAndWait()
                if on_done:
                    on_done()
            except Exception as exc:
                if on_error:
                    on_error(exc)
            finally:
                with self._lock:
                    try:
                        if self._engine:
                            self._engine.stop()
                    except Exception:
                        pass
                    self._engine = None

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            try:
                if self._engine is not None:
                    self._engine.stop()
            except Exception:
                pass
            self._engine = None
