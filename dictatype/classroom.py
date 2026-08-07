from __future__ import annotations

import json
import random
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .db import Database
from .scoring import calculate_wpm, score_text


STUDENT_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DictaType Classroom</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#151c33;--soft:#222c4b;--text:#f6f8ff;--muted:#aab3cd;--accent:#7c9cff;--good:#65d6a7;--bad:#ff7a91}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;background:radial-gradient(circle at top,#182447,var(--bg) 48%);color:var(--text);min-height:100vh}
main{width:min(850px,92vw);margin:40px auto}.card{background:color-mix(in srgb,var(--panel) 94%,transparent);border:1px solid #2d385c;border-radius:22px;padding:26px;box-shadow:0 20px 70px #0007}.hidden{display:none}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.badge{display:inline-block;padding:5px 10px;border-radius:999px;background:var(--soft);color:var(--muted);font-size:13px}label{display:block;color:var(--muted);margin:14px 0 7px}input,textarea,button{font:inherit}input,textarea{width:100%;border:1px solid #354064;background:#0e1529;color:var(--text);border-radius:12px;padding:12px}textarea{min-height:250px;resize:vertical}button{border:0;border-radius:12px;padding:12px 17px;background:var(--accent);color:#071020;font-weight:750;cursor:pointer}button.secondary{background:var(--soft);color:var(--text)}button:disabled{opacity:.45;cursor:not-allowed}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.status{color:var(--muted);margin:14px 0}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}.metric{background:#0e1529;border:1px solid #2b365a;border-radius:14px;padding:14px}.metric strong{display:block;font-size:25px}.warning{color:#ffd483}@media(max-width:650px){.row,.metrics{grid-template-columns:1fr 1fr}}
</style>
</head>
<body><main>
<section id="join" class="card">
<h1>DictaType Classroom</h1><p class="status">Enter the class code shown by your teacher.</p>
<div class="row"><div><label>Your name</label><input id="name" autocomplete="name"></div><div><label>Class</label><input id="className"></div></div>
<label>Session code</label><input id="code" inputmode="numeric" maxlength="6">
<div class="actions"><button onclick="joinSession()">Join session</button></div><p id="joinError" class="warning"></p>
</section>
<section id="exercise" class="card hidden">
<div><span id="language" class="badge"></span> <span id="difficulty" class="badge"></span></div>
<h1 id="title"></h1><p id="progress" class="status"></p>
<div class="actions"><button id="listen" onclick="speakCurrent()">▶ Listen</button><button id="next" class="secondary" onclick="nextSentence()">Next sentence</button></div>
<label>Type what you hear</label><textarea id="answer" spellcheck="false" autocomplete="off" onpaste="return false"></textarea>
<div class="actions"><button onclick="submitAnswer()">Submit answer</button></div><p id="exerciseStatus" class="status"></p>
</section>
<section id="result" class="card hidden"><h1>Submitted</h1><p id="resultMessage" class="status"></p><div id="metrics" class="metrics"></div></section>
</main>
<script>
let lesson=null,index=0,replays=0,startedAt=0,sessionCode='';
const $=id=>document.getElementById(id);
async function joinSession(){
 sessionCode=$('code').value.trim(); const name=$('name').value.trim();
 if(!name||!sessionCode){$('joinError').textContent='Please enter your name and session code.';return;}
 try{const response=await fetch('/api/session?code='+encodeURIComponent(sessionCode));if(!response.ok)throw new Error(await response.text());lesson=await response.json();
 $('title').textContent=lesson.title;$('language').textContent=lesson.language==='fr'?'Français':'English';$('difficulty').textContent=lesson.difficulty;
 $('join').classList.add('hidden');$('exercise').classList.remove('hidden');startedAt=Date.now();updateProgress();setTimeout(speakCurrent,350);
 }catch(error){$('joinError').textContent=error.message||'Could not join the session.';}
}
function voiceForLanguage(){const voices=speechSynthesis.getVoices();const prefix=lesson.language==='fr'?'fr':'en';return voices.find(v=>v.lang.toLowerCase().startsWith(prefix))||voices[0];}
function speakCurrent(){
 if(!lesson)return;if(lesson.replay_limit>0&&replays>=lesson.replay_limit*lesson.sentences.length){$('exerciseStatus').textContent='Replay limit reached.';return;}
 speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(lesson.sentences[index]);utterance.lang=lesson.language==='fr'?'fr-FR':'en-GB';utterance.rate=Math.max(.5,Math.min(1.5,lesson.rate/175));const voice=voiceForLanguage();if(voice)utterance.voice=voice;speechSynthesis.speak(utterance);replays++;updateProgress();
}
function nextSentence(){if(index<lesson.sentences.length-1){index++;updateProgress();speakCurrent();}else{$('exerciseStatus').textContent='This is the final sentence. Review your answer and submit.';}}
function updateProgress(){$('progress').textContent=`Sentence ${index+1} of ${lesson.sentences.length} · Replays used: ${replays}`;$('next').disabled=index>=lesson.sentences.length-1;}
async function submitAnswer(){
 const answer=$('answer').value; if(!answer.trim()){ $('exerciseStatus').textContent='Please type an answer before submitting.';return; }
 const payload={code:sessionCode,name:$('name').value.trim(),class_name:$('className').value.trim(),answer,duration_seconds:Math.max(1,Math.round((Date.now()-startedAt)/1000)),replay_count:replays};
 try{const response=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error(await response.text());const data=await response.json();$('exercise').classList.add('hidden');$('result').classList.remove('hidden');
 $('resultMessage').textContent=data.show_results?'Your result has been saved.':'Your response has been sent to the teacher.';
 if(data.show_results){$('metrics').innerHTML=`<div class="metric"><span>Overall</span><strong>${data.overall_score}%</strong></div><div class="metric"><span>Words</span><strong>${data.word_accuracy}%</strong></div><div class="metric"><span>Characters</span><strong>${data.character_accuracy}%</strong></div><div class="metric"><span>WPM</span><strong>${data.wpm}</strong></div>`;}
 }catch(error){$('exerciseStatus').textContent=error.message||'Submission failed.';}
}
window.speechSynthesis.onvoiceschanged=()=>{};
</script></body></html>"""


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except Exception:
        return "127.0.0.1"


class ClassroomServer:
    def __init__(self, db: Database, on_submission: Callable[[], None] | None = None) -> None:
        self.db = db
        self.on_submission = on_submission
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.lesson: dict[str, Any] | None = None
        self.code = ""
        self.port = 0

    @property
    def running(self) -> bool:
        return self.httpd is not None

    @property
    def url(self) -> str:
        return f"http://{local_ip()}:{self.port}" if self.running else ""

    def start(self, lesson: dict[str, Any], port: int = 8765) -> tuple[str, str]:
        self.stop()
        self.lesson = lesson
        self.code = f"{random.randint(0, 999999):06d}"
        server = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "DictaTypeClassroom/1.0"

            def log_message(self, format: str, *args) -> None:
                return

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                self._send(
                    status,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8",
                )

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send(HTTPStatus.OK, STUDENT_PAGE.encode("utf-8"), "text/html; charset=utf-8")
                    return
                if parsed.path == "/api/session":
                    query = parse_qs(parsed.query)
                    if query.get("code", [""])[0] != server.code:
                        self._send(HTTPStatus.FORBIDDEN, b"Invalid session code.", "text/plain; charset=utf-8")
                        return
                    lesson_data = server.lesson or {}
                    from .scoring import split_sentences

                    sentences = split_sentences(str(lesson_data.get("text", "")))
                    if not lesson_data.get("sentence_mode"):
                        sentences = [str(lesson_data.get("text", ""))]
                    self._json(
                        HTTPStatus.OK,
                        {
                            "title": lesson_data.get("title", "Dictation"),
                            "language": lesson_data.get("language", "en"),
                            "difficulty": lesson_data.get("difficulty", "Intermediate"),
                            "rate": lesson_data.get("rate", 175),
                            "replay_limit": lesson_data.get("replay_limit", 3),
                            "sentences": sentences,
                        },
                    )
                    return
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain")

            def do_POST(self) -> None:  # noqa: N802
                if urlparse(self.path).path != "/api/submit":
                    self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain")
                    return
                try:
                    length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except Exception:
                    self._send(HTTPStatus.BAD_REQUEST, b"Invalid request.", "text/plain")
                    return
                if payload.get("code") != server.code:
                    self._send(HTTPStatus.FORBIDDEN, b"Invalid session code.", "text/plain")
                    return
                lesson_data = server.lesson or {}
                answer = str(payload.get("answer", ""))
                result = score_text(
                    str(lesson_data.get("text", "")),
                    answer,
                    str(lesson_data.get("marking_mode", "balanced")),
                )
                duration = max(1, int(payload.get("duration_seconds", 1)))
                wpm = calculate_wpm(answer, duration)
                server.db.save_attempt(
                    {
                        "student_name": str(payload.get("name", "Anonymous")).strip() or "Anonymous",
                        "class_name": str(payload.get("class_name", "")).strip(),
                        "lesson_id": lesson_data.get("id"),
                        "lesson_title": lesson_data.get("title", "Dictation"),
                        "answer": answer,
                        "score_word": result.word_accuracy,
                        "score_char": result.character_accuracy,
                        "overall_score": result.overall_score,
                        "wpm": wpm,
                        "duration_seconds": duration,
                        "replay_count": int(payload.get("replay_count", 0)),
                        "details": result.to_dict(),
                        "source": "classroom",
                    }
                )
                if server.on_submission:
                    try:
                        server.on_submission()
                    except Exception:
                        pass
                show_results = bool(lesson_data.get("show_results", True))
                self._json(
                    HTTPStatus.OK,
                    {
                        "show_results": show_results,
                        "overall_score": result.overall_score if show_results else None,
                        "word_accuracy": result.word_accuracy if show_results else None,
                        "character_accuracy": result.character_accuracy if show_results else None,
                        "wpm": wpm if show_results else None,
                    },
                )

        for candidate in range(port, port + 20):
            try:
                self.httpd = ThreadingHTTPServer(("0.0.0.0", candidate), Handler)
                self.port = candidate
                break
            except OSError:
                continue
        if self.httpd is None:
            raise OSError("No available port was found for Classroom Mode.")
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.url, self.code

    def stop(self) -> None:
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        self.httpd = None
        self.thread = None
        self.lesson = None
        self.code = ""
        self.port = 0
