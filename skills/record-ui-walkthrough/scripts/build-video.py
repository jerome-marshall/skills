#!/usr/bin/env python3
"""Build a validated silent, captioned walkthrough video."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import preview_common as common

VIEW_W = common.VIEW_W
VIEW_H = common.VIEW_H
FPS = 30
FRAME_S = 1.0 / FPS
FONTSIZE = 28
FFMPEG_CANDIDATES = (
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
    "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
)

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIEW_W}
PlayResY: {VIEW_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{FONTSIZE},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1.5,1,2,48,48,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_ts(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    whole_seconds, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def ass_text(text: str) -> str:
    return (
        text.replace("\\", "\\\u2060")
        .replace("{", "\\{{}")
        .replace("\n", "\\N")
    )


def has_subtitles(ffmpeg: str) -> bool:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-h", "filter=subtitles"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "Render text subtitles" in result.stdout


def find_ffmpeg() -> str:
    seen: set[str] = set()
    found = shutil.which("ffmpeg")
    for candidate in ((found,) if found else ()) + FFMPEG_CANDIDATES:
        if (
            candidate
            and candidate not in seen
            and Path(candidate).is_file()
            and has_subtitles(candidate)
        ):
            return candidate
        if candidate:
            seen.add(candidate)
    raise common.PreviewError(
        "no ffmpeg with libass found (`brew install ffmpeg-full`)"
    )


def find_ffprobe(ffmpeg: str) -> str:
    sibling = Path(ffmpeg).parent / "ffprobe"
    if sibling.is_file():
        return str(sibling)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise common.PreviewError(f"no ffprobe next to {ffmpeg}")


def write_ass(directory: Path, items: list[dict]) -> Path:
    events = [
        "Dialogue: 0,"
        f"{ass_ts(item['captionStart'])},{ass_ts(item['captionEnd'])},"
        f"Default,,0,0,0,,{ass_text(item['description'])}"
        for item in items
    ]
    path = directory / "demo.ass"
    path.write_text(ASS_HEADER + "\n".join(events) + "\n")
    return path


def video_filter(steps: list[dict], items: list[dict]) -> str:
    count = 2 * len(steps) + 1
    filters = [
        f"[0:v]fps={FPS},split={count}"
        + "".join(f"[x{index}]" for index in range(count))
    ]
    parts: list[str] = []

    def freeze(
        source: str, start: float, keep: float, total: float, tag: str
    ) -> str:
        pad = max(0.0, total - keep)
        filters.append(
            f"[{source}]trim={start:.3f}:{start + keep:.3f},"
            f"setpts=PTS-STARTPTS,tpad=stop_mode=clone:"
            f"stop_duration={pad:.3f}[{tag}]"
        )
        return f"[{tag}]"

    first_start = float(steps[0]["start"])
    parts.append(freeze("x0", first_start, FRAME_S, common.LEAD_S, "lead"))
    source_index = 1
    for index, (step, item) in enumerate(zip(steps, items)):
        start = float(step["start"])
        footage = float(item["footageDuration"])
        parts.append(
            freeze(
                f"x{source_index}",
                start,
                footage,
                float(item["pieceDuration"]),
                f"beat{index}",
            )
        )
        source_index += 1
        if index + 1 < len(steps):
            edge = max(start, float(step["end"]) - FRAME_S)
            parts.append(
                freeze(
                    f"x{source_index}",
                    edge,
                    FRAME_S,
                    common.GAP_S,
                    f"gap{index}",
                )
            )
            source_index += 1
    last = steps[-1]
    outro_start = max(float(last["start"]), float(last["end"]) - FRAME_S)
    parts.append(
        freeze(
            f"x{source_index}",
            outro_start,
            FRAME_S,
            common.OUTRO_S,
            "outro",
        )
    )
    filters.append(
        "".join(parts)
        + f"concat=n={len(parts)}:v=1:a=0,"
        "subtitles=demo.ass,format=yuv420p[v]"
    )
    return ";".join(filters)


def render(directory: Path, mode: str = "silent") -> Path:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe(ffmpeg)
    _, workflow, webm, _ = common.load_recording(directory, ffprobe)
    steps = workflow["steps"]
    spoken = [len(step["description"].split()) / 2.5 for step in steps]
    items, duration = common.timeline(steps, spoken)
    write_ass(directory, items)
    common.write_render_review(directory, mode, items, duration)

    output = directory / "walkthrough.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(webm),
            "-filter_complex",
            video_filter(steps, items),
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "-movflags",
            "+faststart",
            str(output),
        ],
        cwd=directory,
        check=True,
    )
    print(f"wrote {output} ({duration:.1f}s silent)")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scratch", nargs="?")
    parser.add_argument("--print-ffmpeg", action="store_true")
    args = parser.parse_args()
    try:
        if args.print_ffmpeg:
            print(find_ffmpeg())
            return 0
        if not args.scratch:
            parser.error("scratch is required")
        render(Path(args.scratch).resolve())
        return 0
    except (common.PreviewError, subprocess.CalledProcessError) as exc:
        print(f"build-video: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
