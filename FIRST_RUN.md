# DictaType First-Run Guide

This guide is for **DictaType 1.0.0-rc.1**.

## 1. Install or extract DictaType

For normal use, run `DictaType-Setup.exe`. The portable ZIP is useful for testing or running without installation.

Windows may show an unknown-publisher warning while the release is unsigned. Only install a build you downloaded from the project's official release page or a source you trust.

## 2. Secure the teacher account

Open **Teacher** on the login screen. On a fresh database, DictaType starts with the initial PIN `1234` and immediately asks the teacher to replace it with a private 6 to 12 digit PIN before teacher tools are available.

Student profiles do not use passwords or PINs.

## 3. Test speech

Open **Settings & security** and choose **Test French neural voice**. A public Windows build should include the offline `fr_FR-siwis-medium` neural voice.

For English, DictaType uses compatible voices installed in Windows.

## 4. Create a dictation

Open **Dictations > New dictation**. Enter the passage, choose the language and voice, then use **Preview voice**. In this release, Preview Voice reads the **complete passage**, allowing the teacher to check pronunciation and pacing before saving.

## 5. Choose the activity type

- **Student practice** is for an individual student using the desktop app.
- **Classroom** serves one selected dictation to student browsers on the local network.
- **Exam** can contain multiple passages and stores each passage under the same exam session.

## 6. Back up before important sessions

Use **Settings & security > Back up database** before formal exams or major changes. Store the backup on a different drive or secure network location when possible.

## 7. Where data is stored

DictaType stores its SQLite database under the current Windows user's application-data folder. Use **Open data folder** in Settings to locate it safely.

## Release-candidate note

`1.0.0-rc.1` is intended for public testing before the final `1.0.0` release. If you encounter a repeatable problem, record the DictaType version, Windows version, what you were doing, and any error message shown on screen.
