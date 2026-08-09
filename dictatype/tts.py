from __future__ import annotations

import gc
import importlib.util
import io
import os
import re
import sys
import tempfile
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None

# Piper/ONNX is intentionally imported lazily. On a 4 GB/HDD classroom PC,
# loading the neural stack during normal application startup wastes memory and
# makes the first window appear much more slowly. The module is loaded only
# when French neural audio is actually generated.
_PiperVoice = None
_SynthesisConfig = None
_piper_import_attempted = False
_piper_import_error = ""


def _load_piper_api():
    global _PiperVoice, _SynthesisConfig, _piper_import_attempted, _piper_import_error
    if _piper_import_attempted:
        return _PiperVoice, _SynthesisConfig
    _piper_import_attempted = True
    try:
        from piper import PiperVoice as PiperVoiceClass, SynthesisConfig as SynthesisConfigClass

        _PiperVoice = PiperVoiceClass
        _SynthesisConfig = SynthesisConfigClass
        _piper_import_error = ""
    except Exception as exc:
        _PiperVoice = None
        _SynthesisConfig = None
        _piper_import_error = f"{type(exc).__name__}: {exc}"
    return _PiperVoice, _SynthesisConfig

try:  # Windows-only playback for the bundled neural voice.
    import winsound
except Exception:  # pragma: no cover
    winsound = None


BUNDLED_FRENCH_VOICE_ID = "dictatype:piper:fr_FR-siwis-medium"
BUNDLED_FRENCH_MODEL = "fr_FR-siwis-medium.onnx"
BUNDLED_FRENCH_NAME = "DictaType French Neural"


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    languages: tuple[str, ...]

    @property
    def display_name(self) -> str:
        language_text = ", ".join(self.languages) if self.languages else "System"
        if self.id == BUNDLED_FRENCH_VOICE_ID:
            return f"{self.name} · fr-FR · Built-in offline (recommended)"
        return f"{self.name} · {language_text}"


def _resource_root() -> Path:
    # PyInstaller one-file builds extract bundled data under _MEIPASS.
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


def bundled_french_model_path() -> Path:
    return _resource_root() / "assets" / "voices" / BUNDLED_FRENCH_MODEL


def bundled_french_config_path() -> Path:
    return Path(str(bundled_french_model_path()) + ".json")


def builtin_french_available() -> bool:
    # Keep the normal startup check cheap. The build pipeline performs a full
    # synthesis verification against the frozen EXE before artifacts are
    # published, so this lightweight check is safe for low-memory machines.
    try:
        piper_present = importlib.util.find_spec("piper") is not None
    except Exception:
        piper_present = False
    return (
        piper_present
        and bundled_french_model_path().is_file()
        and bundled_french_config_path().is_file()
    )


def french_voice_diagnostics(*, synthesize: bool = False) -> dict[str, object]:
    """Return precise built-in French voice diagnostics.

    When *synthesize* is True this imports Piper, loads the bundled model and
    creates a short WAV. GitHub Actions uses this against the finished EXE so
    a release cannot silently ship without a working neural French voice.
    """
    model = bundled_french_model_path()
    config = bundled_french_config_path()
    result: dict[str, object] = {
        "ready": False,
        "model_path": str(model),
        "config_path": str(config),
        "model_exists": model.is_file(),
        "config_exists": config.is_file(),
        "piper_importable": False,
        "synthesis_ok": False,
        "reason": "",
    }
    if not model.is_file():
        result["reason"] = "French neural model file is missing from the application bundle."
        return result
    if not config.is_file():
        result["reason"] = "French neural model configuration is missing from the application bundle."
        return result

    PiperVoiceClass, SynthesisConfigClass = _load_piper_api()
    if PiperVoiceClass is None or SynthesisConfigClass is None:
        result["reason"] = (
            "Piper runtime could not be loaded"
            + (f" ({_piper_import_error})" if _piper_import_error else ".")
        )
        return result
    result["piper_importable"] = True

    if synthesize:
        try:
            fd, temp_name = tempfile.mkstemp(prefix="dictatype_fr_verify_", suffix=".wav")
            os.close(fd)
            Path(temp_name).unlink(missing_ok=True)
            ok = render_speech_wav_file(
                "Bonjour, ceci est un test de la voix française de DictaType.",
                temp_name,
                language="fr",
                voice_id=BUNDLED_FRENCH_VOICE_ID,
                rate=145,
                clarity_mode=True,
                prefer_builtin_french=True,
            )
            result["synthesis_ok"] = bool(ok)
            try:
                Path(temp_name).unlink(missing_ok=True)
            except Exception:
                pass
            release_bundled_french_voice()
            if not ok:
                result["reason"] = "Piper loaded, but the bundled French model could not synthesize WAV audio."
                return result
        except Exception as exc:
            result["reason"] = f"French neural synthesis failed ({type(exc).__name__}: {exc})"
            return result
    else:
        result["synthesis_ok"] = True

    result["ready"] = True
    result["reason"] = "Built-in French neural voice is ready."
    return result


def builtin_french_voice() -> Voice:
    return Voice(
        id=BUNDLED_FRENCH_VOICE_ID,
        name=BUNDLED_FRENCH_NAME,
        languages=("fr-FR",),
    )


def _decode_language(value) -> str:
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            value = str(value)
    value = str(value).replace("\x05", "").replace("_", "-")
    return value or "system"


def list_voices() -> list[Voice]:
    voices: list[Voice] = []

    # Put the dedicated French voice first so new French dictations choose it
    # automatically. It is independent of Windows language packs.
    if builtin_french_available():
        voices.append(builtin_french_voice())

    if pyttsx3 is None:
        return voices
    try:
        engine = pyttsx3.init()
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
    except Exception:
        pass
    return voices


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


def _voice_matches_language(raw_voice, language: str) -> bool:
    haystack = " ".join(
        [
            str(getattr(raw_voice, "id", "")),
            str(getattr(raw_voice, "name", "")),
            *[_decode_language(item) for item in (getattr(raw_voice, "languages", []) or [])],
        ]
    ).casefold()
    if language == "fr":
        return any(token in haystack for token in ("fr-", "fr_", "french", "français", "hortense", "denise"))
    return any(token in haystack for token in ("en-", "en_", "english", "zira", "david", "mark", "hazel"))


_piper_lock = threading.RLock()
_piper_voice = None


def _get_piper_french_voice():
    global _piper_voice
    if not builtin_french_available():
        return None
    PiperVoiceClass, _ = _load_piper_api()
    if PiperVoiceClass is None:
        return None
    with _piper_lock:
        if _piper_voice is None:
            # Piper automatically looks for <model>.onnx.json beside the model.
            _piper_voice = PiperVoiceClass.load(str(bundled_french_model_path()))
        return _piper_voice


def release_bundled_french_voice() -> None:
    """Release the loaded neural session after exam audio has been prepared."""
    global _piper_voice
    with _piper_lock:
        _piper_voice = None
    # ONNX owns native buffers that can be sizeable compared with a 4 GB PC.
    # A collection here is intentional because this runs at an explicit audio
    # preparation boundary, not continuously during typing.
    gc.collect()


def _piper_length_scale(rate: int, clarity_mode: bool) -> float:
    # Piper uses a length scale rather than words-per-minute. 1.0 is the model's
    # normal pace, and values > 1 are slower. Dictation clarity defaults to a
    # measured, deliberate pace without stretching speech unnaturally.
    target_rate = max(90, min(240, int(rate or 175)))
    if clarity_mode:
        target_rate = min(target_rate, 145)
    return max(0.72, min(1.65, 175.0 / target_rate))


def _render_piper_french_wav_bytes(
    text: str,
    *,
    rate: int = 175,
    volume: float = 1.0,
    clarity_mode: bool = False,
) -> bytes | None:
    if not str(text).strip():
        return None
    voice = _get_piper_french_voice()
    _, SynthesisConfigClass = _load_piper_api()
    if voice is None or SynthesisConfigClass is None:
        return None
    try:
        syn_config = SynthesisConfigClass(
            volume=max(0.0, min(1.5, float(volume))),
            length_scale=_piper_length_scale(rate, clarity_mode),
            noise_scale=0.667,
            noise_w_scale=0.8,
            normalize_audio=True,
        )
        buffer = io.BytesIO()
        # A single loaded voice session is reused to keep exam playback fast.
        # Synthesis is serialized because ONNX voice sessions are not treated as
        # re-entrant by DictaType.
        with _piper_lock:
            with wave.open(buffer, "wb") as wav_file:
                voice.synthesize_wav(str(text), wav_file, syn_config=syn_config)
        audio = buffer.getvalue()
        if len(audio) > 44 and audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
            return audio
    except Exception:
        return None
    return None


def render_speech_wav_file(
    text: str,
    output_path: str | Path,
    *,
    language: str = "en",
    voice_id: str = "",
    rate: int = 175,
    volume: float = 1.0,
    clarity_mode: bool = False,
    prefer_builtin_french: bool = False,
) -> bool:
    """Render directly to a WAV file without retaining the whole file in RAM."""
    text = str(text)
    if not text.strip():
        return False
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if language == "fr" and (voice_id == BUNDLED_FRENCH_VOICE_ID or prefer_builtin_french):
        voice = _get_piper_french_voice()
        _, SynthesisConfigClass = _load_piper_api()
        if voice is not None and SynthesisConfigClass is not None:
            try:
                syn_config = SynthesisConfigClass(
                    volume=max(0.0, min(1.5, float(volume))),
                    length_scale=_piper_length_scale(rate, clarity_mode),
                    noise_scale=0.667,
                    noise_w_scale=0.8,
                    normalize_audio=True,
                )
                with _piper_lock:
                    with wave.open(str(path), "wb") as wav_file:
                        voice.synthesize_wav(text, wav_file, syn_config=syn_config)
                if _valid_wav_file(path):
                    return True
            except Exception:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

    if pyttsx3 is None:
        return False

    effective_rate = int(rate)
    if clarity_mode and language == "fr":
        effective_rate = min(effective_rate, 150)
    engine = None
    try:
        # pyttsx3/SAPI can write directly to the target file too.
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        engine = pyttsx3.init()
        chosen_id = str(voice_id or "").strip()
        if chosen_id == BUNDLED_FRENCH_VOICE_ID:
            chosen_id = ""
        voices = engine.getProperty("voices") or []
        if chosen_id:
            try:
                engine.setProperty("voice", chosen_id)
            except Exception:
                chosen_id = ""
        if not chosen_id:
            for raw_voice in voices:
                if _voice_matches_language(raw_voice, language):
                    candidate = str(getattr(raw_voice, "id", ""))
                    if candidate:
                        engine.setProperty("voice", candidate)
                        break
        engine.setProperty("rate", effective_rate)
        engine.setProperty("volume", max(0.0, min(1.0, float(volume))))
        engine.save_to_file(text, str(path))
        engine.runAndWait()
        engine.stop()
        engine = None
        return _valid_wav_file(path)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return False
    finally:
        try:
            if engine is not None:
                engine.stop()
        except Exception:
            pass


def _valid_wav_file(path: Path) -> bool:
    try:
        if path.stat().st_size <= 44:
            return False
        with path.open("rb") as handle:
            header = handle.read(12)
        return header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    except Exception:
        return False


def render_speech_wav_bytes(
    text: str,
    *,
    language: str = "en",
    voice_id: str = "",
    rate: int = 175,
    volume: float = 1.0,
    clarity_mode: bool = False,
    prefer_builtin_french: bool = False,
) -> bytes | None:
    """Render speech to WAV for classroom delivery.

    French can use DictaType's bundled Piper neural voice. This avoids the
    common problem where a Windows PC has no real French TTS voice and an
    English voice tries to pronounce French text. Windows SAPI remains the
    fallback for compatibility and for teachers who explicitly prefer it.
    """
    if not str(text).strip():
        return None

    if language == "fr" and (voice_id == BUNDLED_FRENCH_VOICE_ID or prefer_builtin_french):
        neural_audio = _render_piper_french_wav_bytes(
            text,
            rate=rate,
            volume=volume,
            clarity_mode=clarity_mode,
        )
        if neural_audio:
            return neural_audio

    if pyttsx3 is None:
        return None

    effective_rate = int(rate)
    if clarity_mode and language == "fr":
        effective_rate = min(effective_rate, 150)

    path = ""
    engine = None
    try:
        fd, path = tempfile.mkstemp(prefix="dictatype_speech_", suffix=".wav")
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass

        engine = pyttsx3.init()
        chosen_id = str(voice_id or "").strip()
        if chosen_id == BUNDLED_FRENCH_VOICE_ID:
            chosen_id = ""
        voices = engine.getProperty("voices") or []
        if chosen_id:
            try:
                engine.setProperty("voice", chosen_id)
            except Exception:
                chosen_id = ""
        if not chosen_id:
            for raw_voice in voices:
                if _voice_matches_language(raw_voice, language):
                    candidate = str(getattr(raw_voice, "id", ""))
                    if candidate:
                        engine.setProperty("voice", candidate)
                        break

        engine.setProperty("rate", effective_rate)
        engine.setProperty("volume", max(0.0, min(1.0, float(volume))))
        engine.save_to_file(str(text), path)
        engine.runAndWait()
        engine.stop()
        engine = None

        audio = Path(path).read_bytes()
        if len(audio) > 44 and audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
            return audio
        return None
    except Exception:
        return None
    finally:
        try:
            if engine is not None:
                engine.stop()
        except Exception:
            pass
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


class SpeechEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._engine = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def available(self) -> bool:
        return pyttsx3 is not None or builtin_french_available()

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
        self._stop_event.clear()

        def worker() -> None:
            temp_path = ""
            try:
                if voice_id == BUNDLED_FRENCH_VOICE_ID:
                    if winsound is None:
                        raise RuntimeError("Built-in neural voice playback is available in the Windows build.")
                    fd, temp_path = tempfile.mkstemp(prefix="dictatype_french_", suffix=".wav")
                    os.close(fd)
                    if not render_speech_wav_file(
                        text,
                        temp_path,
                        language="fr",
                        voice_id=BUNDLED_FRENCH_VOICE_ID,
                        rate=rate,
                        volume=volume,
                    ):
                        raise RuntimeError(
                            "The built-in French neural voice could not generate audio. "
                            "DictaType can still use an installed Windows French voice."
                        )
                    if not self._stop_event.is_set():
                        winsound.PlaySound(temp_path, winsound.SND_FILENAME | winsound.SND_SYNC)
                    if on_done and not self._stop_event.is_set():
                        on_done()
                    return

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
                if on_done and not self._stop_event.is_set():
                    on_done()
            except Exception as exc:
                if on_error and not self._stop_event.is_set():
                    on_error(exc)
            finally:
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
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
        self._stop_event.set()
        with self._lock:
            try:
                if self._engine is not None:
                    self._engine.stop()
            except Exception:
                pass
            self._engine = None
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
