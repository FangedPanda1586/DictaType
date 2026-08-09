# Security Policy

## Reporting a security issue

Please report security issues privately to the repository maintainer rather than publishing exploit details in a public issue. If the repository provides a GitHub Security Advisory / private vulnerability reporting option, prefer that channel.

Include the DictaType version, Windows version, steps to reproduce, and the minimum technical details needed to understand the issue. Do not attach real student databases unless they have been fully anonymised.

## Security model

DictaType is a local-first classroom application. The teacher PIN protects ordinary access to teacher-only screens, while Windows user-account security protects the local files themselves. Keep the Windows account secure and protect database backups as educational records.

Student profiles intentionally do not use passwords or PINs.

## Classroom and exam networking

Classroom and exam sessions operate on the local network. Use trusted classroom networks and stop the session when it is no longer needed.

DictaType reduces unnecessary exposure by serving the active local session only, but it is not intended to replace operating-system hardening, managed examination browsers, or institutional network controls for high-stakes adversarial examinations.

## Backups

Backups can contain student names, classes, answers, scores, comments, and lesson content. Store them according to the privacy and retention requirements that apply to your school or organisation.
