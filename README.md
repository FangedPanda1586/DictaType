# DictaType

**DictaType** is a local-first, open-source English and French dictation and typing assessment application for Windows. It is designed for teachers, training centres, classrooms, and students who need structured dictation practice without a cloud account or subscription.

> Current public build: **1.0.0-rc.1 (Release Candidate 1)**

![DictaType icon](assets/dictatype.png)

## Highlights

- English and French dictation
- Built-in offline Piper neural French voice (`fr_FR-siwis-medium`)
- Windows system voices for English and fallback speech
- Teacher-created dictations with TXT and DOCX import
- Full-passage voice preview before saving
- Sentence Mode and Passage Mode
- Replay limits, timers, speech rate, and optional spoken punctuation
- Flexible, Balanced, and Strict marking
- Accent, capitalisation, punctuation, missing-word, and extra-word analysis
- WPM, timing, replay, and accuracy statistics
- Student profiles with history across practice, classroom, and exam attempts
- Classroom mode for one dictation over the local network
- Exam mode with multiple passages grouped into one exam session
- Individual result PDFs and combined multi-passage exam PDFs
- CSV and Excel exports
- Teacher PIN protection, lockout, and automatic inactivity locking
- Local SQLite backup and restore
- Automatic low-memory/HDD performance mode
- No built-in ads, telemetry, cloud account, or subscription

## Download and install

For most users, download and run:

```text
DictaType-Setup.exe
```

A portable package is also published:

```text
DictaType-Portable-Windows.zip
```

The portable build contains the same ONEDIR runtime as the installer, including Piper, eSpeak, ONNX Runtime, and the French voice files.

### Windows security warning

The RC1 installer is prepared for public testing but may be **unsigned** unless the release maintainer has configured code signing. Windows can therefore display an unknown-publisher or reputation warning. Verify that the file came from the project's official release page before running it.

## First run

Read [FIRST_RUN.md](FIRST_RUN.md) for the short setup checklist.

On a fresh database, the initial teacher PIN is `1234`. DictaType requires the teacher to replace it with a new 6 to 12 digit PIN before teacher tools are unlocked.

Students do not use passwords or student PINs. They identify themselves with their name and class.

## Dictation modes

### Sentence Mode

The passage is split into sentences. Students can move through Previous / Next sentence controls, subject to the replay limit configured by the teacher.

### Passage Mode

The entire passage is played continuously. Sentence navigation is hidden and the replay limit applies to the complete passage.

## Voice preview

**Preview voice reads the complete passage** in RC1. This lets a teacher hear names, accents, punctuation handling, pacing, and pronunciation before saving the dictation.

Preview behaviour does not change student replay limits.

## Classroom and exam sessions

### Classroom

The teacher selects exactly one dictation. Students on the same local network open the address shown by DictaType in a modern browser and submit their work to the teacher computer.

### Exam

The teacher can select multiple passages. DictaType stores every passage separately while grouping them under the same exam session. A combined PDF can be generated for the whole exam.

The teacher computer generates the French neural audio so students hear the same pronunciation. Student computers only need to receive and play the generated audio.

## Performance on older PCs

**Automatic** performance mode is recommended. DictaType can select a low-memory/HDD profile on weaker machines. The neural French model is loaded only when needed, generated audio is cached to disk, and the model can be released from memory after generation.

For formal classroom or exam use, pre-generating audio before students join reduces load during the session.

## Privacy and local data

DictaType has no built-in advertising, analytics, telemetry, or cloud account. Desktop lessons, profiles, results, comments, and settings are stored in a local SQLite database.

Classroom and exam browser traffic stays on the local network between student browsers and the teacher computer. As with any LAN application, network administrators can still observe network traffic on infrastructure they control.

Use **Settings & security > Open data folder** to locate the current user's data directory, and use the built-in backup function before important sessions.

## Reports and exports

Teachers can review attempts, add comments, export CSV/Excel data, save individual PDF reports, and produce one combined PDF for a multi-passage exam.

Historical attempts store an expected-text snapshot so later lesson edits do not rewrite the content of newer stored results.

## Build from source

DictaType's Windows CI uses Python 3.12, PyInstaller ONEDIR, and Inno Setup.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean DictaType.spec
```

The GitHub Actions workflow additionally downloads the French voice, verifies Piper in normal Python, verifies neural synthesis inside the finished frozen EXE, builds the installer, and creates the portable ZIP.

## Creating RC1 on GitHub

After the public-release patch has been committed and the workflow passes, create and push the tag:

```text
v1.0.0-rc.1
```

The GitHub Actions workflow publishes the installer and portable ZIP as a **pre-release** and generates release notes automatically.

## Licence and third-party notices

DictaType is licensed under **GNU GPL v3.0 or later**. See [LICENSE](LICENSE).

The Windows build also contains third-party speech and runtime components. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md), especially the attribution information for Piper and the bundled SIWIS French voice.

## Release status

This is a **release candidate**, not the final 1.0.0 build. RC1 is intended to test fresh installation, upgrades, French neural speech, classroom/exam operation, reporting, backup/restore, and performance on machines outside the development environment before promoting the project to 1.0.0.
