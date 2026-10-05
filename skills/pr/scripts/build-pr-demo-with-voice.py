#!/usr/bin/env python3
"""Build a validated voiced and captioned pr demo video."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import preview_common as common

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pr_demo_silent", HERE / "build-pr-demo.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load silent renderer")
SILENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SILENT)

TTS_RATE = 24000
HOLD_WARN_S = 5.0


class TtsFailed(RuntimeError):
    """Voice generation failed after preview inputs passed validation."""


def warn(message: str) -> None:
    print(f"build-pr-demo-with-voice: warning: {message}", file=sys.stderr)


def run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or exc.stdout or "").strip().splitlines()[-4:]
        raise TtsFailed(
            f"{' '.join(command[:3])} failed\n" + "\n".join(tail)
        ) from exc


def duration(ffprobe: str, media: Path) -> float:
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise TtsFailed(f"cannot probe generated audio {media}") from exc


def synthesize(
    python: Path,
    models: Path,
    steps: list[dict],
    voice_dir: Path,
    voice: str,
    speed: float,
) -> list[Path]:
    voice_dir.mkdir(exist_ok=True)
    for stale in voice_dir.glob("beat-*.wav"):
        stale.unlink()
    lines = voice_dir / "lines.json"
    lines.write_text(json.dumps([step["description"] for step in steps]))
    run(
        [
            str(python),
            str(HERE / "kokoro-tts.py"),
            str(models),
            str(lines),
            str(voice_dir),
            "--voice",
            voice,
            "--speed",
            str(speed),
        ]
    )
    outputs = [voice_dir / f"beat-{index}.wav" for index in range(len(steps))]
    missing = [path.name for path in outputs if not path.is_file()]
    if missing:
        raise TtsFailed(f"no wav emitted for {', '.join(missing)}")
    return outputs


def master_audio(
    ffmpeg: str,
    beat_wavs: list[Path],
    items: list[dict],
    output: Path,
) -> None:
    inputs: list[str] = []
    filters: list[str] = []
    chain: list[str] = []

    def silence(seconds: float, tag: str) -> None:
        if seconds <= 0.001:
            return
        filters.append(f"anullsrc=r={TTS_RATE}:cl=mono:d={seconds:.3f}[s{tag}]")
        chain.append(f"[s{tag}]")

    silence(common.LEAD_S, "lead")
    for index, (wav, item) in enumerate(zip(beat_wavs, items)):
        input_index = len(inputs) // 2
        inputs.extend(["-i", str(wav)])
        pre = float(item["captionStart"]) - float(item["pieceStart"])
        post = float(item["pieceEnd"]) - float(item["captionEnd"])
        silence(pre, f"pre{index}")
        filters.append(
            f"[{input_index}:a]aformat=sample_rates={TTS_RATE}:"
            f"channel_layouts=mono[v{index}]"
        )
        chain.append(f"[v{index}]")
        silence(post, f"post{index}")
        if index + 1 < len(items):
            silence(common.GAP_S, f"gap{index}")
    silence(common.OUTRO_S, "outro")
    filters.append("".join(chain) + f"concat=n={len(chain)}:v=0:a=1[a]")
    run(
        [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[a]",
            "-c:a",
            "pcm_s16le",
            "-ar",
            str(TTS_RATE),
            "-ac",
            "1",
            str(output),
        ]
    )


def fallback(reason: str, directory: Path) -> int:
    warn(f"{reason}; falling back to silent video")
    try:
        SILENT.render(directory, mode="silent-fallback")
        return 0
    except (common.PreviewError, subprocess.CalledProcessError) as exc:
        print(f"build-pr-demo-with-voice: error: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scratch")
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument(
        "--venv",
        default=os.environ.get("PR_DEMO_TTS_VENV", str(common.VOICE_VENV_DEFAULT)),
    )
    parser.add_argument(
        "--models",
        default=os.environ.get("PR_DEMO_TTS_MODELS", str(common.VOICE_MODELS_DEFAULT)),
    )
    args = parser.parse_args()
    if args.speed <= 0:
        parser.error("--speed must be positive")

    directory = Path(args.scratch).resolve()
    try:
        ffmpeg = SILENT.find_ffmpeg()
        ffprobe = SILENT.find_ffprobe(ffmpeg)
        _, workflow, webm, _ = common.load_recording(directory, ffprobe)
    except common.PreviewError as exc:
        print(f"build-pr-demo-with-voice: error: {exc}", file=sys.stderr)
        return 1

    unsupported = common.voice_unsupported()
    if unsupported:
        return fallback(unsupported, directory)
    python = Path(args.venv) / "bin" / "python"
    if not python.is_file():
        return fallback(f"no voice stack at {args.venv}", directory)
    models = Path(args.models)
    missing = [name for name in common.VOICE_MODEL_FILES if not (models / name).is_file()]
    if missing:
        return fallback(f"missing voice models in {models}: {', '.join(missing)}", directory)

    voice_dir = directory / "voice"
    try:
        beat_wavs = synthesize(
            python,
            models,
            workflow["steps"],
            voice_dir,
            args.voice,
            args.speed,
        )
        spoken = [duration(ffprobe, wav) for wav in beat_wavs]
        items, total = common.timeline(workflow["steps"], spoken)
        for item in items:
            hold = float(item["pieceDuration"]) - float(item["footageDuration"])
            if hold > HOLD_WARN_S:
                warn(
                    f"beat {item['index']} holds a still for {hold:.1f}s; "
                    "tighten the line"
                )
        SILENT.write_ass(directory, items)
        common.write_render_review(directory, "voiced", items, total)
        narration = voice_dir / "narration.wav"
        master_audio(ffmpeg, beat_wavs, items, narration)

        output = directory / "pr-demo.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(webm),
                "-i",
                str(narration),
                "-filter_complex",
                SILENT.video_filter(workflow["steps"], items),
                "-map",
                "[v]",
                "-map",
                "1:a",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output),
            ],
            cwd=directory,
            check=True,
        )
        print(f"wrote {output} ({total:.1f}s voiced, voice {args.voice})")
        return 0
    except (TtsFailed, subprocess.CalledProcessError) as exc:
        return fallback(f"TTS failed ({exc})", directory)


if __name__ == "__main__":
    sys.exit(main())
