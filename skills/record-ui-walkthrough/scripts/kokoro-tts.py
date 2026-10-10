#!/usr/bin/env python3
"""Synthesize one wav per line with Kokoro-82M through kokoro-onnx and misaki.

Runs inside the voice venv, not the caller's Python.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("models", help="directory holding the Kokoro model files")
    parser.add_argument("lines", help="JSON file with a list of lines to speak")
    parser.add_argument("out", help="directory for beat-<n>.wav")
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    import soundfile as sf
    from kokoro_onnx import Kokoro
    from misaki import en, espeak

    g2p = en.G2P(
        trf=False, british=False, fallback=espeak.EspeakFallback(british=False)
    )
    models = Path(args.models)
    kokoro = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = json.loads(Path(args.lines).read_text())
    for index, text in enumerate(lines):
        phonemes, _ = g2p(text)
        if "❓" in phonemes:
            print(f"beat {index}: unpronounceable word in {text!r}", file=sys.stderr)
            return 1
        samples, rate = kokoro.create(
            phonemes, args.voice, speed=args.speed, is_phonemes=True
        )
        sf.write(out / f"beat-{index}.wav", samples, rate)
        print(f"beat {index}: {phonemes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
