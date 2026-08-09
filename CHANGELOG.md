# Changelog

## 1.0.0-rc.1

Public release candidate for DictaType 1.0.

### Added

- Public-facing About & Licensing screen accessible from the login screen and teacher Settings.
- Bundled offline Piper `fr_FR-siwis-medium` French neural voice in Windows builds.
- THIRD-PARTY-NOTICES with French voice attribution and speech-runtime licensing information.
- First-run guide and public release documentation staged into installer and portable builds.
- GitHub pre-release packaging for the `v1.0.0-rc.1` tag.
- BUILD-INFO.txt in packaged builds with release and GitHub Actions build identifiers.

### Changed

- **Preview Voice now reads the complete dictation passage**, rather than only the first sentence or first 300 characters.
- Windows packaging uses PyInstaller ONEDIR for more reliable Piper/eSpeak/ONNX loading and less startup extraction overhead on HDD-based PCs.
- French classroom/exam speech is generated on the teacher computer and reused by student browsers.
- Documentation now reflects Classroom versus Exam sessions, student history, combined exam PDFs, and adaptive low-memory performance mode.

### Fixed

- Exam/classroom startup no longer freezes the teacher interface while French neural audio is generated. Exam audio is prepared on a background worker and cached to disk before students are allowed to join.
- Classroom & Exams now has a full-page vertical scrollbar for smaller displays.
- A compact Room Details banner stays at the top of the Classroom & Exams page and immediately shows the student address, session code, readiness state, and audio-preparation progress.
- Students who try to join an exam before background audio preparation is complete now receive a clear wait-and-retry message instead of entering a half-prepared room.
- Local French student exercises now automatically use the bundled DictaType French neural voice when available, including older lessons that were saved with a Windows/SAPI voice.
- Editing an existing French dictation now selects the bundled neural voice by default so Preview Voice and saved settings stay consistent.
- Settings & Security now has vertical scrolling and mouse-wheel support so every option remains reachable on smaller displays.
- Python 3.12 Windows playback compatibility by avoiding a hard dependency on `winsound.SND_SYNC`, which is not present in Python 3.12.
- French voice packaging, staging, and finished-EXE verification in GitHub Actions.
- Windows SQLite restore locking by closing the verification connection before replacing the database.

## 1.0.0 development baseline

- English and French dictation.
- Custom teacher lessons and imports.
- Sentence and passage playback modes.
- Flexible, balanced, and strict marking.
- Student history and classroom/exam result tracking.
- CSV/Excel exports and PDF reporting.
- Teacher security controls and local backup/restore.
