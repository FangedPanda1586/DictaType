# DictaType

**DictaType** is an offline, open-source English and French dictation and typing assessment application for teachers and students. Teachers create their own passages, select an installed Windows voice, configure the exercise, and review detailed results. Students hear the passage without seeing it and type what they heard.

![DictaType icon](dictatype.ico)

## Main features

- English and French dictation using voices already installed in Windows
- Custom teacher-created passages
- TXT and DOCX passage import
- Sentence-by-sentence or full-passage playback
- Speech rate, replay limit and time-limit controls
- Optional spoken punctuation
- Flexible, balanced and strict marking modes
- French accent, capitalisation and punctuation analysis
- Word accuracy, character accuracy, WPM, duration and replay statistics
- Local student register and result history
- CSV and Excel exports
- HTML result reports and teacher comments
- Teacher dashboard protected by a hashed local PIN
- Automatic SQLite storage, backup and restore
- Dark and light themes
- Offline local classroom mode for student browsers on the same network
- Portable Windows executable and installer build automation
- No cloud account, advertisements, telemetry or subscription

## Student workflow

1. Enter or select a student name.
2. Select a dictation.
3. Listen to each sentence.
4. Type the dictated passage.
5. Submit the answer.
6. View the score when the teacher has enabled student results.

Copy and paste are disabled inside the controlled desktop exercise editor.

## Teacher workflow

The default teacher PIN on first launch is `1234`. Change it from **Settings**.

The teacher dashboard allows you to:

- create, edit, duplicate, delete, import and export dictations;
- manage students and classes;
- inspect word-level corrections;
- add private comments;
- export filtered results to CSV or Excel;
- save individual HTML reports;
- back up and restore the complete local database.

## Local classroom mode

The teacher selects a dictation and starts a classroom session. DictaType shows a local address and six-digit code. Students connected to the same network open that address in a modern browser, enter the code, listen using their browser's installed system voice, and submit their answers to the teacher computer.

The classroom server works without an internet account. Windows Firewall may ask the teacher to allow local-network access the first time it starts.

> Classroom browser mode is intended for ordinary supervised lessons. Because a browser must receive the passage to speak it, it is not designed as a high-security examination system against technically advanced inspection tools.

## Run from source on Windows

Requirements:

- Windows 10 or Windows 11
- Python 3.10 to 3.12
- At least one installed English or French text-to-speech voice

Double-click:

```text
run_windows.bat
```

Or run manually:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

## Build the Windows executable

Double-click:

```text
build_windows.bat
```

The portable application will be created at:

```text
dist\DictaType.exe
```

When Inno Setup 6 is installed, the script also creates:

```text
installer_output\DictaType-Setup.exe
```

## Build automatically with GitHub

See [GITHUB_BUILD_GUIDE.md](GITHUB_BUILD_GUIDE.md) for the complete upload and build procedure.

In summary:

1. Create a GitHub repository without adding another README, licence, or `.gitignore`.
2. Upload the contents of this project so `.github/workflows/windows-build.yml` is at the repository root.
3. Open the repository's **Actions** tab.
4. Run **Build Windows release**.
5. Download the `DictaType-Windows` artifact.

The workflow installs its own Windows build dependencies, runs the tests, creates the portable executable, and creates the installer. Pushing a tag such as `v1.0.0` also creates a GitHub release containing both files.

## Data location

DictaType stores data locally:

```text
%APPDATA%\DictaType\dictatype.db
```

The database contains lessons, students, results and application settings. Use the built-in backup command rather than manually copying the database while DictaType is open.

## Installed Windows voices

DictaType does not download or bundle voice packs. It detects system voices through the Windows speech engine. Additional voices can be managed from Windows language and accessibility settings.

## Repository layout

```text
dictatype/                 Application source
sample_lessons/            Importable English and French examples
tests/                     Automated tests
assets/                    Application icons
docs/                      User and technical documentation
.github/workflows/         Automated Windows builds
DictaType.spec             PyInstaller build definition
installer.iss              Inno Setup installer definition
```

## Licence

DictaType is licensed under the **GNU General Public License v3.0 or later**. You may use, study, modify and redistribute it under the terms of that licence.

## Privacy

DictaType does not include analytics, telemetry, advertising or external accounts. Desktop lessons and results remain in the local SQLite database. Local classroom submissions travel only across the teacher's local network to the teacher computer.
