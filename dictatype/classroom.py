from __future__ import annotations

import json
import random
import socket
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .db import Database
from .scoring import calculate_wpm, score_text, split_sentences


STUDENT_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DictaType Classroom</title>
<style>
:root{color-scheme:light;--bg:#eef2f6;--panel:#fff;--soft:#e4ebf2;--text:#283746;--muted:#6f7e8d;--accent:#a9d8ff;--accentStrong:#4b9fe6;--border:#d2dae3;--good:#42a982;--bad:#d95d69}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;background:linear-gradient(145deg,#f4f6f8,#e8f3fc);color:var(--text);min-height:100vh}
main{width:min(900px,94vw);margin:34px auto}.card{background:var(--panel);border:1px solid var(--border);border-radius:22px;padding:28px;box-shadow:0 18px 60px #48607818}.hidden{display:none}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.badge{display:inline-block;padding:6px 11px;border-radius:999px;background:var(--soft);color:var(--muted);font-size:13px}label{display:block;color:var(--muted);margin:14px 0 7px}input,textarea,button{font:inherit}input,textarea{width:100%;border:1px solid var(--border);background:#f8fafc;color:var(--text);border-radius:14px;padding:13px}textarea{min-height:285px;resize:vertical}button{border:0;border-radius:14px;padding:12px 18px;background:var(--accent);color:#16324a;font-weight:750;cursor:pointer}button.primary{background:var(--accentStrong);color:white}button.secondary{background:var(--soft);color:var(--text)}button:disabled{opacity:.45;cursor:not-allowed}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.status{color:var(--muted);margin:12px 0}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}.metric{background:#f8fafc;border:1px solid var(--border);border-radius:16px;padding:14px}.metric strong{display:block;font-size:25px}.warning{color:#aa5a24}.examline{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:14px}@media(max-width:650px){.row,.metrics{grid-template-columns:1fr}.card{padding:20px}main{margin:18px auto}}
</style>
</head>
<body><main>
<section id="join" class="card">
<h1>DictaType Classroom</h1><p class="status">Enter your name exactly as it should appear on the teacher's results.</p>
<div class="row"><div><label>Your name</label><input id="name" autocomplete="name"></div><div><label>Class</label><input id="className"></div></div>
<label>Session code</label><input id="code" inputmode="numeric" maxlength="6">
<div class="actions"><button class="primary" onclick="joinSession()">Join session</button></div><p id="joinError" class="warning"></p>
</section>
<section id="exercise" class="card hidden">
<div class="examline"><div><span id="language" class="badge"></span> <span id="difficulty" class="badge"></span> <span id="mode" class="badge"></span></div><strong id="examProgress"></strong></div>
<h1 id="title"></h1><p id="progress" class="status"></p>
<div class="actions"><button id="listen" class="primary" onclick="speakCurrent()">▶ Listen</button><button id="previous" class="secondary" onclick="previousSentence()">Previous</button><button id="next" class="secondary" onclick="nextSentence()">Next sentence</button></div>
<label>Type what you hear</label><textarea id="answer" spellcheck="false" autocomplete="off" onpaste="return false"></textarea>
<div class="actions"><button id="submit" class="primary" onclick="submitAnswer()">Submit</button></div><p id="exerciseStatus" class="status"></p>
</section>
<section id="result" class="card hidden"><h1>Exam submitted</h1><p id="resultMessage" class="status"></p><div id="metrics" class="metrics"></div></section>
</main>
<script>
let exam=null,itemIndex=0,sentenceIndex=0,playCounts={},startedAt=0,sessionCode='',visibleScores=[];
const $=id=>document.getElementById(id);
function currentItem(){return exam&&exam.items?exam.items[itemIndex]:null;}
async function joinSession(){
 sessionCode=$('code').value.trim(); const name=$('name').value.trim();
 if(!name||!sessionCode){$('joinError').textContent='Please enter your name and session code.';return;}
 try{const response=await fetch('/api/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:sessionCode,name,class_name:$('className').value.trim()})});if(!response.ok)throw new Error(await response.text());exam=await response.json();
 itemIndex=0;visibleScores=[];$('join').classList.add('hidden');$('exercise').classList.remove('hidden');renderItem(true);
 }catch(error){$('joinError').textContent=error.message||'Could not join the session.';}
}
function renderItem(autoSpeak){const lesson=currentItem();if(!lesson)return;sentenceIndex=0;playCounts={};startedAt=Date.now();$('answer').value='';$('exerciseStatus').textContent='';
 $('title').textContent=lesson.title;$('language').textContent=lesson.language==='fr'?'Français':'English';$('difficulty').textContent=lesson.difficulty;$('mode').textContent=lesson.sentence_mode?'Sentence mode':'Passage mode';
 $('examProgress').textContent=exam.items.length>1?`${exam.exam_title} · Passage ${itemIndex+1} of ${exam.items.length}`:'Classroom dictation';
 $('previous').style.display=lesson.sentence_mode?'inline-block':'none';$('next').style.display=lesson.sentence_mode?'inline-block':'none';$('submit').textContent=itemIndex===exam.items.length-1?(exam.items.length>1?'Submit final passage':'Submit answer'):'Submit passage & continue';updateProgress();if(autoSpeak)setTimeout(speakCurrent,350);}
function voiceForLanguage(){const lesson=currentItem();const voices=speechSynthesis.getVoices();const prefix=lesson.language==='fr'?'fr':'en';return voices.find(v=>v.lang.toLowerCase().startsWith(prefix))||voices[0];}
function speakCurrent(){const lesson=currentItem();if(!lesson)return;const count=playCounts[sentenceIndex]||0;if(lesson.replay_limit>0&&count>=lesson.replay_limit+1){$('exerciseStatus').textContent=lesson.sentence_mode?'The replay limit for this sentence has been reached.':'The replay limit for this passage has been reached.';return;}
 speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(lesson.sentences[sentenceIndex]);utterance.lang=lesson.language==='fr'?'fr-FR':'en-GB';utterance.rate=Math.max(.5,Math.min(1.5,lesson.rate/175));const voice=voiceForLanguage();if(voice)utterance.voice=voice;speechSynthesis.speak(utterance);playCounts[sentenceIndex]=count+1;updateProgress();}
function previousSentence(){const lesson=currentItem();if(lesson&&lesson.sentence_mode&&sentenceIndex>0){sentenceIndex--;updateProgress();}}
function nextSentence(){const lesson=currentItem();if(lesson&&lesson.sentence_mode&&sentenceIndex<lesson.sentences.length-1){sentenceIndex++;updateProgress();speakCurrent();}else{$('exerciseStatus').textContent='This is the final sentence. Review your answer and submit.';}}
function updateProgress(){const lesson=currentItem();if(!lesson)return;const count=playCounts[sentenceIndex]||0;const replayText=lesson.replay_limit===0?'Unlimited replays':`${Math.max(0,count-1)}/${lesson.replay_limit} replays`;if(lesson.sentence_mode){$('progress').textContent=`Sentence ${sentenceIndex+1} of ${lesson.sentences.length} · ${replayText}`;$('previous').disabled=sentenceIndex<=0;$('next').disabled=sentenceIndex>=lesson.sentences.length-1;}else{$('progress').textContent=`Passage mode · ${replayText}`;}}
function totalPlays(){return Object.values(playCounts).reduce((a,b)=>a+b,0);}
async function submitAnswer(){const answer=$('answer').value;if(!answer.trim()){$('exerciseStatus').textContent='Please type an answer before submitting.';return;}const payload={code:sessionCode,name:$('name').value.trim(),class_name:$('className').value.trim(),answer,duration_seconds:Math.max(1,Math.round((Date.now()-startedAt)/1000)),replay_count:totalPlays(),item_index:itemIndex};
 $('submit').disabled=true;try{const response=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error(await response.text());const data=await response.json();if(data.show_results&&data.overall_score!==null)visibleScores.push(Number(data.overall_score));
 if(itemIndex<exam.items.length-1){itemIndex++;renderItem(true);$('exerciseStatus').textContent='Previous passage saved. Continue with the next passage.';}else{finishExam(data);}
 }catch(error){$('exerciseStatus').textContent=error.message||'Submission failed.';}finally{$('submit').disabled=false;}}
function finishExam(data){$('exercise').classList.add('hidden');$('result').classList.remove('hidden');$('resultMessage').textContent=`All ${exam.items.length} passage(s) were saved under ${$('name').value.trim()}.`;if(visibleScores.length===exam.items.length){const avg=visibleScores.reduce((a,b)=>a+b,0)/visibleScores.length;$('metrics').innerHTML=`<div class="metric"><span>Passages</span><strong>${exam.items.length}</strong></div><div class="metric"><span>Average</span><strong>${avg.toFixed(1)}%</strong></div>`;}else{$('metrics').innerHTML='';}}
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
        self.lesson: dict[str, Any] | None = None  # Backward-compatible alias for first item.
        self.lessons: list[dict[str, Any]] = []
        self.exam_title = ""
        self.session_id = ""
        self.allow_new_profiles = True
        self.code = ""
        self.port = 0
        self._submitted_items: set[tuple[int, int]] = set()
        self._submission_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self.httpd is not None

    @property
    def url(self) -> str:
        return f"http://{local_ip()}:{self.port}" if self.running else ""

    def _public_item(self, lesson_data: dict[str, Any]) -> dict[str, Any]:
        sentences = split_sentences(str(lesson_data.get("text", "")))
        if not lesson_data.get("sentence_mode"):
            sentences = [str(lesson_data.get("text", ""))]
        return {
            "id": lesson_data.get("id"),
            "title": lesson_data.get("title", "Dictation"),
            "language": lesson_data.get("language", "en"),
            "difficulty": lesson_data.get("difficulty", "Intermediate"),
            "rate": lesson_data.get("rate", 175),
            "replay_limit": lesson_data.get("replay_limit", 3),
            "sentence_mode": bool(lesson_data.get("sentence_mode", 1)),
            "sentences": sentences,
        }

    def start(
        self,
        lessons: dict[str, Any] | list[dict[str, Any]],
        port: int = 8765,
        exam_title: str = "",
        allow_new_profiles: bool = True,
    ) -> tuple[str, str]:
        self.stop()
        self.lessons = [lessons] if isinstance(lessons, dict) else list(lessons)
        self.lessons = [item for item in self.lessons if item and str(item.get("text", "")).strip()]
        if not self.lessons:
            raise ValueError("Select at least one dictation or passage.")
        self.lesson = self.lessons[0]
        self.exam_title = exam_title.strip() or (
            self.lesson.get("title", "Classroom Dictation")
            if len(self.lessons) == 1
            else "Classroom Exam"
        )
        self.session_id = uuid.uuid4().hex
        self.allow_new_profiles = bool(allow_new_profiles)
        self.code = f"{random.randint(0, 999999):06d}"
        self._submitted_items.clear()
        server = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "DictaTypeClassroom/1.1"

            def log_message(self, format: str, *args) -> None:
                return

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

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
                    self._json(
                        HTTPStatus.OK,
                        {
                            "exam_title": server.exam_title,
                            "item_count": len(server.lessons),
                            "items": [server._public_item(item) for item in server.lessons],
                        },
                    )
                    return
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain")

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path not in {"/api/join", "/api/submit"}:
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
                if path == "/api/join":
                    name = str(payload.get("name", "")).strip()
                    class_name = str(payload.get("class_name", "")).strip()
                    if not name:
                        self._send(HTTPStatus.BAD_REQUEST, b"Student name is required.", "text/plain")
                        return
                    student = server.db.find_student(name, class_name)
                    if student is None:
                        if not server.allow_new_profiles:
                            self._send(HTTPStatus.FORBIDDEN, b"This exam only accepts registered student profiles. Check your name and class with the teacher.", "text/plain; charset=utf-8")
                            return
                        try:
                            student = server.db.create_student_profile(name, class_name)
                        except ValueError as exc:
                            self._send(HTTPStatus.FORBIDDEN, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
                            return
                    if not bool(student.get("active", 1)):
                        self._send(HTTPStatus.FORBIDDEN, b"This student profile is disabled.", "text/plain; charset=utf-8")
                        return
                    self._json(
                        HTTPStatus.OK,
                        {
                            "exam_title": server.exam_title,
                            "item_count": len(server.lessons),
                            "items": [server._public_item(item) for item in server.lessons],
                        },
                    )
                    return
                try:
                    item_index = int(payload.get("item_index", 0))
                except Exception:
                    item_index = -1
                if item_index < 0 or item_index >= len(server.lessons):
                    self._send(HTTPStatus.BAD_REQUEST, b"Invalid passage number.", "text/plain")
                    return
                name = str(payload.get("name", "")).strip()
                class_name = str(payload.get("class_name", "")).strip()
                if not name:
                    self._send(HTTPStatus.BAD_REQUEST, b"Student name is required.", "text/plain")
                    return
                student = server.db.find_student(name, class_name)
                if student is None:
                    if not server.allow_new_profiles:
                        self._send(HTTPStatus.FORBIDDEN, b"This exam only accepts registered student profiles.", "text/plain; charset=utf-8")
                        return
                    student = server.db.ensure_student_profile(name, class_name)
                if not bool(student.get("active", 1)):
                    self._send(HTTPStatus.FORBIDDEN, b"This student profile is disabled.", "text/plain; charset=utf-8")
                    return
                key = (int(student["id"]), item_index)
                with server._submission_lock:
                    if key in server._submitted_items:
                        self._send(HTTPStatus.CONFLICT, b"This passage has already been submitted for this student.", "text/plain; charset=utf-8")
                        return
                    server._submitted_items.add(key)
                lesson_data = server.lessons[item_index]
                answer = str(payload.get("answer", ""))
                result = score_text(str(lesson_data.get("text", "")), answer, str(lesson_data.get("marking_mode", "balanced")))
                duration = max(1, int(payload.get("duration_seconds", 1)))
                wpm = calculate_wpm(answer, duration)
                try:
                    server.db.save_attempt(
                        {
                            "student_id": student.get("id"),
                            "student_name": student.get("name", name),
                            "class_name": student.get("class_name", class_name),
                            "lesson_id": lesson_data.get("id"),
                            "lesson_title": lesson_data.get("title", f"Passage {item_index + 1}"),
                            "answer": answer,
                            "score_word": result.word_accuracy,
                            "score_char": result.character_accuracy,
                            "overall_score": result.overall_score,
                            "wpm": wpm,
                            "duration_seconds": duration,
                            "replay_count": int(payload.get("replay_count", 0)),
                            "details": result.to_dict(),
                            "source": "classroom-exam" if len(server.lessons) > 1 else "classroom",
                            "exam_session_id": server.session_id,
                            "exam_title": server.exam_title,
                            "exam_item_index": item_index + 1,
                            "exam_item_count": len(server.lessons),
                        }
                    )
                except Exception:
                    with server._submission_lock:
                        server._submitted_items.discard(key)
                    raise
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
                        "item_index": item_index + 1,
                        "item_count": len(server.lessons),
                        "finished": item_index + 1 >= len(server.lessons),
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
        self.lessons = []
        self.exam_title = ""
        self.session_id = ""
        self.allow_new_profiles = True
        self.code = ""
        self.port = 0
        self._submitted_items.clear()
