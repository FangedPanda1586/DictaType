# DictaType Third-Party Notices

DictaType includes or depends on third-party open-source software and data. This summary is provided for attribution and redistribution convenience. It does not replace the original licence texts supplied by each upstream project.

## Piper text-to-speech

DictaType's built-in French neural speech uses **Piper** from the Open Home Foundation / OHF-Voice project.

- Project: `OHF-Voice/piper1-gpl`
- Licence: GNU General Public License v3.0 or later (GPL-3.0-or-later)
- Upstream: https://github.com/OHF-Voice/piper1-gpl

Piper embeds eSpeak NG for phonemisation.

## eSpeak NG

- Project: `espeak-ng/espeak-ng`
- Licence: GNU General Public License v3.0 or later (GPL-3.0-or-later)
- Upstream: https://github.com/espeak-ng/espeak-ng

## ONNX Runtime

Piper uses ONNX Runtime for neural-network inference.

- Project: `microsoft/onnxruntime`
- Licence: MIT
- Upstream: https://github.com/microsoft/onnxruntime

## Bundled French voice: fr_FR-siwis-medium

The Windows release downloads and redistributes the Piper voice **fr_FR-siwis-medium** from the `rhasspy/piper-voices` collection.

- Voice collection: https://huggingface.co/rhasspy/piper-voices
- Voice model card: `fr/fr_FR/siwis/medium/MODEL_CARD`
- Language: French (France)
- Quality: medium

The voice model card identifies the training dataset as **The SIWIS French Speech Synthesis Database** and states the dataset licence as **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

Dataset attribution:

> Yamagishi, Junichi; Honnet, Pierre-Edouard; Garner, Philip; Lazaridis, Alexandros. (2017). The SIWIS French Speech Synthesis Database, 2016 [dataset]. University of Edinburgh, School of Informatics, Centre for Speech Technology Research. DOI: 10.7488/ds/1705.

The `rhasspy/piper-voices` repository is labelled MIT, while Piper's own voice documentation instructs redistributors to review each voice's model card for voice-specific licensing information. Keep this notice with redistributed DictaType builds.

## Other Python dependencies

DictaType also uses libraries including `pyttsx3`, `python-docx`, `openpyxl`, `pywin32`, and `ReportLab`. Their copyright notices and licence terms remain the property of their respective authors. The source repository and Python package metadata identify the dependency versions used for a build.

## DictaType

DictaType itself is distributed under **GPL-3.0-or-later**. See `LICENSE` in the source repository and installed application folder.
