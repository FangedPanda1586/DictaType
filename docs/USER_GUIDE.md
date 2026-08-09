# DictaType User Guide

This guide applies to **DictaType 1.0.0-rc.1**.

## First launch

DictaType opens on the Student / Teacher sign-in screen. Students use their name and class. They do not need a password or PIN.

A fresh teacher database begins with PIN `1234`, but DictaType requires the teacher to replace it with a private 6 to 12 digit PIN before teacher tools can be used.

## Add a dictation

1. Sign in as **Teacher**.
2. Open **Dictations** and choose **New dictation**.
3. Enter a title, language, difficulty, and optional category.
4. Type the passage or import a TXT/DOCX file.
5. Select a voice.
6. Choose **Preview voice** to hear the **entire passage**.
7. Configure speech rate, replay limit, time limit, and marking mode.
8. Choose Sentence Mode or Passage Mode.
9. Save the dictation.

A replay limit of `0` means unlimited replays. A time limit of `0` means no timer deadline.

## Sentence Mode

Sentence Mode divides the passage into sentences. Students receive Previous / Next sentence controls and replay limits are counted per sentence.

## Passage Mode

Passage Mode reads the whole passage continuously. Sentence navigation is hidden and the replay limit applies to the whole passage.

## Marking modes

### Flexible

Designed for listening practice. It is more forgiving of case, punctuation, and accents.

### Balanced

Recommended for most classroom work. It scores spelling while separately reporting accent, capitalisation, and punctuation issues.

### Strict

Designed for formal typing assessments where exact text matters more heavily.

## Student practice

1. Enter the same name and class used previously, or create a profile.
2. Select a dictation.
3. Start the exercise.
4. Listen within the configured replay limit.
5. Type the answer.
6. Submit.
7. View the result if the teacher enabled student results.

Student history can include practice, classroom, and exam attempts.

## Classroom mode

Classroom mode uses **one selected dictation**.

1. Connect teacher and student devices to the same local network.
2. Open **Classroom / Exam** on the teacher computer.
3. Choose Classroom and select a dictation.
4. Start the session.
5. Give students the displayed address and session code.
6. Students open the address in a modern browser.
7. Stop the session when finished.

For French, DictaType can generate the neural audio on the teacher computer so all students receive the same pronunciation.

## Exam mode

Exam mode can contain **multiple passages**. Each submitted passage is stored separately but linked to the same student and exam session.

Teachers can create a combined PDF containing the exam summary and all passages for correction.

## Results

Teacher results can include:

- score and accuracy;
- WPM and duration;
- replay counts;
- missing, extra, and substituted words;
- accent, capitalisation, and punctuation issues;
- expected text and student answer;
- teacher comments;
- individual PDF export;
- combined full-exam PDF export;
- CSV and Excel exports.

## French neural voice

Open **Settings & security > Test French neural voice**. The Windows public build should contain the `fr_FR-siwis-medium` model under the application's `voices` folder.

If the built-in neural voice is unavailable, DictaType can fall back to compatible Windows/browser speech where supported.

## Performance

Use **Automatic (recommended)** unless there is a reason to override it. Automatic mode can select a low-memory/HDD profile for weaker computers.

For exams, allow DictaType to pre-generate audio before students join. Generated WAV audio can then be reused instead of repeatedly loading the neural model.

## Backup and restore

Use **Settings & security > Back up database** regularly and before formal exams.

Restore replaces the current local database. Create a fresh backup before restoring an older copy.

## About and licences

Choose **About DictaType** from the login screen or teacher Settings to see the app version, licence, privacy summary, and French voice attribution. Public builds include `LICENSE` and `THIRD-PARTY-NOTICES.md` in the application folder.
