from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Iterable

WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+(?:['’\-][\wÀ-ÖØ-öø-ÿ]+)*", re.UNICODE)
PUNCT_RE = re.compile(r"[^\w\sÀ-ÖØ-öø-ÿ]", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n+")


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def split_sentences(text: str) -> list[str]:
    parts = [clean_spaces(part) for part in SENTENCE_RE.split(text) if clean_spaces(part)]
    return parts or ([clean_spaces(text)] if clean_spaces(text) else [])


def tokenize_words(text: str) -> list[str]:
    return WORD_RE.findall(clean_spaces(text))


def punctuation_sequence(text: str) -> list[str]:
    return PUNCT_RE.findall(text)


def levenshtein(a: Iterable[str], b: Iterable[str]) -> int:
    left = list(a)
    right = list(b)
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (left_item != right_item)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def similarity_score(expected: Iterable[str], actual: Iterable[str]) -> float:
    expected_list = list(expected)
    actual_list = list(actual)
    denominator = max(len(expected_list), 1)
    distance = levenshtein(expected_list, actual_list)
    return max(0.0, 100.0 * (1.0 - distance / denominator))


@dataclass
class Change:
    kind: str
    expected: str = ""
    actual: str = ""
    position: int = 0


@dataclass
class ScoreResult:
    mode: str
    overall_score: float
    word_accuracy: float
    character_accuracy: float
    punctuation_accuracy: float
    capitalization_accuracy: float
    expected_word_count: int
    actual_word_count: int
    correct_words: int
    substitutions: int
    missing_words: int
    extra_words: int
    accent_mistakes: int
    capitalization_mistakes: int
    punctuation_mistakes: int
    changes: list[Change] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["changes"] = [asdict(change) for change in self.changes]
        return payload


def _score_tokens(words: list[str], mode: str) -> list[str]:
    if mode == "strict":
        return words
    lowered = [word.casefold() for word in words]
    if mode == "flexible":
        return [strip_accents(word) for word in lowered]
    return lowered


def _changes(expected_words: list[str], actual_words: list[str]) -> list[Change]:
    matcher = SequenceMatcher(a=expected_words, b=actual_words, autojunk=False)
    changes: list[Change] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            pair_count = min(i2 - i1, j2 - j1)
            for offset in range(pair_count):
                changes.append(
                    Change(
                        "replace",
                        expected_words[i1 + offset],
                        actual_words[j1 + offset],
                        i1 + offset,
                    )
                )
            for index in range(i1 + pair_count, i2):
                changes.append(Change("missing", expected_words[index], "", index))
            for index in range(j1 + pair_count, j2):
                changes.append(Change("extra", "", actual_words[index], i1 + pair_count))
        elif tag == "delete":
            for index in range(i1, i2):
                changes.append(Change("missing", expected_words[index], "", index))
        elif tag == "insert":
            for index in range(j1, j2):
                changes.append(Change("extra", "", actual_words[index], i1))
    return changes


def score_text(expected: str, actual: str, mode: str = "balanced") -> ScoreResult:
    mode = mode if mode in {"strict", "balanced", "flexible"} else "balanced"
    expected = clean_spaces(expected)
    actual = clean_spaces(actual)
    expected_words_original = tokenize_words(expected)
    actual_words_original = tokenize_words(actual)
    expected_words = _score_tokens(expected_words_original, mode)
    actual_words = _score_tokens(actual_words_original, mode)

    word_accuracy = similarity_score(expected_words, actual_words)

    if mode == "strict":
        expected_chars = list(expected)
        actual_chars = list(actual)
    elif mode == "balanced":
        expected_chars = list(expected.casefold())
        actual_chars = list(actual.casefold())
    else:
        expected_chars = list(strip_accents(re.sub(r"[^\w\s]", "", expected.casefold())))
        actual_chars = list(strip_accents(re.sub(r"[^\w\s]", "", actual.casefold())))
    character_accuracy = similarity_score(expected_chars, actual_chars)

    expected_punctuation = punctuation_sequence(expected)
    actual_punctuation = punctuation_sequence(actual)
    punctuation_accuracy = similarity_score(expected_punctuation, actual_punctuation)
    punctuation_mistakes = levenshtein(expected_punctuation, actual_punctuation)

    pair_count = min(len(expected_words_original), len(actual_words_original))
    capitalization_mistakes = 0
    accent_mistakes = 0
    for index in range(pair_count):
        exp = expected_words_original[index]
        act = actual_words_original[index]
        if exp.casefold() == act.casefold() and exp != act:
            capitalization_mistakes += 1
        elif strip_accents(exp).casefold() == strip_accents(act).casefold() and exp.casefold() != act.casefold():
            accent_mistakes += 1

    capitalization_accuracy = max(
        0.0,
        100.0 * (1.0 - capitalization_mistakes / max(len(expected_words_original), 1)),
    )

    changes = _changes(expected_words, actual_words)
    substitutions = sum(change.kind == "replace" for change in changes)
    missing_words = sum(change.kind == "missing" for change in changes)
    extra_words = sum(change.kind == "extra" for change in changes)
    correct_words = max(
        0,
        len(expected_words_original) - substitutions - missing_words,
    )

    if mode == "strict":
        overall = 0.65 * word_accuracy + 0.25 * character_accuracy + 0.10 * punctuation_accuracy
    elif mode == "balanced":
        overall = 0.80 * word_accuracy + 0.10 * character_accuracy + 0.05 * punctuation_accuracy + 0.05 * capitalization_accuracy
    else:
        overall = 0.85 * word_accuracy + 0.15 * character_accuracy

    return ScoreResult(
        mode=mode,
        overall_score=round(overall, 2),
        word_accuracy=round(word_accuracy, 2),
        character_accuracy=round(character_accuracy, 2),
        punctuation_accuracy=round(punctuation_accuracy, 2),
        capitalization_accuracy=round(capitalization_accuracy, 2),
        expected_word_count=len(expected_words_original),
        actual_word_count=len(actual_words_original),
        correct_words=correct_words,
        substitutions=substitutions,
        missing_words=missing_words,
        extra_words=extra_words,
        accent_mistakes=accent_mistakes,
        capitalization_mistakes=capitalization_mistakes,
        punctuation_mistakes=punctuation_mistakes,
        changes=changes,
    )


def calculate_wpm(answer: str, duration_seconds: int) -> float:
    if duration_seconds <= 0:
        return 0.0
    standard_words = len(answer) / 5.0
    return round(standard_words / (duration_seconds / 60.0), 1)
