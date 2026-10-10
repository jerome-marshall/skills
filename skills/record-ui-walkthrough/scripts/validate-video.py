#!/usr/bin/env python3
"""Mechanical review gates for record-ui-walkthrough artifacts."""

from __future__ import annotations

import argparse
import importlib.util
import math
import re
import subprocess
import sys
from pathlib import Path

import preview_common as common

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "walkthrough_silent", HERE / "build-video.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load renderer helpers")
SILENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SILENT)


def clean_review(directory: Path, prefix: str) -> Path:
    review = directory / "review"
    review.mkdir(exist_ok=True)
    for path in review.glob(f"{prefix}-*.png"):
        path.unlink()
    return review


def extract_frame(
    ffmpeg: str,
    media: Path,
    timestamp: float,
    output: Path,
) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(media),
            "-frames:v",
            "1",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def gate_shots(directory: Path) -> None:
    shot_list = common.load_shot_list(directory)
    print(
        f"shots ok: {len(shot_list['claims'])} claims, "
        f"{len(shot_list['surfaces'])} surfaces"
    )


def gate_preflight(directory: Path) -> None:
    shot_list, _ = common.load_preflight(directory)
    print(
        f"preflight ok: {len(shot_list['surfaces'])} representative surfaces; "
        "locators, enabled state, paint, and screencast are ready"
    )


def gate_record(directory: Path, ffmpeg: str, ffprobe: str) -> None:
    shot_list, workflow, webm, duration = common.load_recording(directory, ffprobe)
    review = clean_review(directory, "record")
    for index, step in enumerate(workflow["steps"]):
        output = review / f"record-{step['surface']}-{index}.png"
        extract_frame(ffmpeg, webm, float(step["time"]), output)
    print(
        f"record ok: {len(workflow['steps'])} clips cover "
        f"{len(shot_list['surfaces'])} surfaces in {duration:.2f}s"
    )
    print(f"inspect {review}/record-*.png before rendering")


def mean_volume(
    ffmpeg: str,
    media: Path,
    start: float,
    end: float,
) -> float:
    result = subprocess.run(
        [
            ffmpeg,
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{max(0.02, end - start):.3f}",
            "-i",
            str(media),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"mean_volume:\s+(-inf|-?\d+(?:\.\d+)?)\s+dB", result.stderr)
    if not match or match.group(1) == "-inf":
        return -math.inf
    return float(match.group(1))


def validate_render_manifest(
    directory: Path,
    workflow: dict,
    duration: float,
) -> tuple[str, list[dict]]:
    manifest = common.read_json(directory / "render-review.json")
    mode = common.nonempty(manifest.get("mode"), "render-review.mode")
    common.require(
        mode in {"voiced", "silent", "silent-fallback"},
        f"render-review: bad mode {mode}",
    )
    declared_duration = common.number(
        manifest.get("duration"), "render-review.duration"
    )
    common.require(
        abs(declared_duration - duration) <= 0.25,
        f"render duration mismatch: declared {declared_duration}, actual {duration}",
    )
    items = manifest.get("steps")
    common.require(
        isinstance(items, list) and len(items) == len(workflow["steps"]),
        "render-review step count mismatch",
    )
    previous_end = 0.0
    for index, (item, source) in enumerate(zip(items, workflow["steps"])):
        common.require(isinstance(item, dict), f"render steps[{index}]: expected object")
        for key in ("surface", "claim", "description"):
            common.require(
                item.get(key) == source.get(key),
                f"render steps[{index}].{key} mismatch",
            )
        piece_start = common.number(
            item.get("pieceStart"), f"render steps[{index}].pieceStart"
        )
        piece_end = common.number(
            item.get("pieceEnd"), f"render steps[{index}].pieceEnd"
        )
        caption_start = common.number(
            item.get("captionStart"), f"render steps[{index}].captionStart"
        )
        caption_end = common.number(
            item.get("captionEnd"), f"render steps[{index}].captionEnd"
        )
        common.require(
            previous_end <= piece_start <= caption_start < caption_end <= piece_end,
            f"render steps[{index}]: invalid timeline",
        )
        previous_end = piece_end
    return mode, items


def gate_render(directory: Path, ffmpeg: str, ffprobe: str) -> None:
    _, workflow, _, _ = common.load_recording(directory, ffprobe)
    output = directory / "walkthrough.mp4"
    video, duration, streams = common.video_info(ffprobe, output)
    common.require(video.get("codec_name") == "h264", "render is not H.264")
    common.require(video.get("pix_fmt") == "yuv420p", "render is not yuv420p")
    common.require(
        (video.get("width"), video.get("height"))
        == (common.VIEW_W, common.VIEW_H),
        "render has wrong dimensions",
    )
    common.require(output.stat().st_size <= 10 * 1024 * 1024, "render exceeds 10MB")
    mode, items = validate_render_manifest(directory, workflow, duration)
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if mode == "voiced":
        common.require(len(audio) == 1, "voiced render needs one audio stream")
    else:
        common.require(not audio, "silent render must not have audio")

    review = clean_review(directory, "render")
    for index, item in enumerate(items):
        midpoint = (float(item["captionStart"]) + float(item["captionEnd"])) / 2
        output_frame = review / f"render-{item['surface']}-{index}.png"
        extract_frame(ffmpeg, output, midpoint, output_frame)
        if mode == "voiced":
            level = mean_volume(
                ffmpeg,
                output,
                float(item["captionStart"]),
                float(item["captionEnd"]),
            )
            common.require(
                level > -55,
                f"caption {index} has no measurable speech ({level} dB)",
            )

    if mode == "voiced":
        manifest = common.read_json(directory / "render-review.json")
        lead = float(manifest["lead"])
        common.require(
            mean_volume(ffmpeg, output, 0, lead) <= -55,
            "lead-in is not silent",
        )
        gap = float(manifest["gap"])
        if gap > 0:
            for index in range(len(items) - 1):
                start = float(items[index]["pieceEnd"])
                common.require(
                    mean_volume(ffmpeg, output, start, start + gap) <= -55,
                    f"gap {index} is not silent",
                )
    print(f"render ok: {mode}, {duration:.2f}s, {len(items)} captions")
    print(f"inspect {review}/render-*.png and play every speech window")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", choices=("shots", "preflight", "record", "render"))
    parser.add_argument("scratch")
    args = parser.parse_args()
    directory = Path(args.scratch).resolve()
    try:
        if args.gate == "shots":
            gate_shots(directory)
        elif args.gate == "preflight":
            gate_preflight(directory)
        else:
            ffmpeg = SILENT.find_ffmpeg()
            ffprobe = SILENT.find_ffprobe(ffmpeg)
            if args.gate == "record":
                gate_record(directory, ffmpeg, ffprobe)
            else:
                gate_render(directory, ffmpeg, ffprobe)
        return 0
    except (
        common.PreviewError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"validate-video: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
