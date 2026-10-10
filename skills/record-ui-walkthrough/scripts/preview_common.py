"""Shared manifest, media, and timeline validation for record-ui-walkthrough."""

from __future__ import annotations

import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

VIEW_W = 1280
VIEW_H = 800
LEAD_S = 0.3
GAP_S = 0.4
OUTRO_S = 0.8
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# The espeak-ng bundled in espeakng-loader's wheels needs GLIBC_2.29 symbols,
# even though the wheels are tagged manylinux_2_17.
VOICE_GLIBC_MIN = (2, 29)
VOICE_MODEL_FILES = {
    "kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
VOICE_VENV_DEFAULT = Path.home() / ".local" / "share" / "pr-demo" / "tts-onnx-venv"
VOICE_MODELS_DEFAULT = Path.home() / ".local" / "share" / "pr-demo" / "kokoro"


def voice_unsupported() -> str | None:
    """Why this host cannot narrate, or None when it can."""
    if sys.platform == "darwin":
        return None
    if sys.platform != "linux":
        return f"voice is unsupported on {sys.platform}"
    name, version = platform.libc_ver()
    if name != "glibc":
        return "voice needs glibc; this system uses another C library"
    try:
        found = tuple(int(part) for part in version.split(".")[:2])
    except ValueError:
        return f"cannot read the glibc version {version!r}"
    if found < VOICE_GLIBC_MIN:
        floor = ".".join(map(str, VOICE_GLIBC_MIN))
        return f"voice needs glibc >= {floor} (found {version})"
    return None


class PreviewError(ValueError):
    """An invalid walkthrough artifact."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreviewError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PreviewError(f"{path}: {exc}") from exc
    require(isinstance(value, dict), f"{path}: expected a JSON object")
    return value


def nonempty(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: expected text")
    return value.strip()


def identifier(value: Any, label: str) -> str:
    result = nonempty(value, label)
    require(bool(ID_RE.fullmatch(result)), f"{label}: invalid id {result!r}")
    return result


def number(value: Any, label: str) -> float:
    require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value),
        f"{label}: expected a finite number",
    )
    return float(value)


def load_shot_list(directory: Path) -> dict[str, Any]:
    manifest = read_json(directory / "shot-list.json")
    claims = manifest.get("claims")
    surfaces = manifest.get("surfaces")
    require(isinstance(claims, list) and claims, "shot-list.json: claims is empty")
    require(
        isinstance(surfaces, list) and surfaces,
        "shot-list.json: surfaces is empty",
    )

    claim_map: dict[str, dict[str, Any]] = {}
    for index, claim in enumerate(claims):
        require(isinstance(claim, dict), f"claims[{index}]: expected object")
        claim_id = identifier(claim.get("id"), f"claims[{index}].id")
        require(claim_id not in claim_map, f"duplicate claim id: {claim_id}")
        nonempty(claim.get("description"), f"claims[{index}].description")
        claim_map[claim_id] = claim

    surface_map: dict[str, dict[str, Any]] = {}
    surfaced_claims: set[str] = set()
    for index, surface in enumerate(surfaces):
        require(isinstance(surface, dict), f"surfaces[{index}]: expected object")
        surface_id = identifier(surface.get("id"), f"surfaces[{index}].id")
        require(surface_id not in surface_map, f"duplicate surface id: {surface_id}")
        nonempty(surface.get("name"), f"surfaces[{index}].name")
        claim_id = identifier(surface.get("claim"), f"surfaces[{index}].claim")
        require(claim_id in claim_map, f"{surface_id}: unknown claim {claim_id}")
        surface_map[surface_id] = surface
        surfaced_claims.add(claim_id)

    require(
        surfaced_claims == set(claim_map),
        "claims without surfaces: "
        + repr(sorted(set(claim_map) - surfaced_claims)),
    )
    return {
        "raw": manifest,
        "claims": claim_map,
        "surfaces": surface_map,
    }


def validate_paint(paint: Any, label: str) -> None:
    require(isinstance(paint, dict), f"{label}: expected object")
    paint_kind = nonempty(paint.get("kind"), f"{label}.kind")
    require(
        paint_kind in {"node", "region", "relation", "none"},
        f"{label}.kind: invalid value {paint_kind}",
    )
    if paint_kind == "relation":
        axis = nonempty(paint.get("axis"), f"{label}.axis")
        order = nonempty(paint.get("order"), f"{label}.order")
        state = nonempty(paint.get("state"), f"{label}.state")
        require(axis in {"vertical", "horizontal"}, f"{label}: bad axis")
        require(
            order in {"a-before-b", "b-before-a"},
            f"{label}: bad relation order",
        )
        require(
            state in {"gap", "flush", "overlap"},
            f"{label}: bad relation state",
        )
        distance = number(paint.get("distance"), f"{label}.distance")
        require(
            (state == "gap" and distance > 0)
            or (state == "flush" and abs(distance) <= 1)
            or (state == "overlap" and distance < 0),
            f"{label}: distance does not match relation state",
        )
    elif paint_kind == "none":
        nonempty(paint.get("reason"), f"{label}.reason")


def load_preflight(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    shot_list = load_shot_list(directory)
    preflight = read_json(directory / "preflight.json")
    require(
        preflight.get("screencastReady") is True,
        "preflight.screencastReady must be true",
    )
    errors = preflight.get("errors", [])
    require(isinstance(errors, list) and not errors, "preflight.errors is not empty")
    surfaces = preflight.get("surfaces")
    require(isinstance(surfaces, list) and surfaces, "preflight.surfaces is empty")
    covered: set[str] = set()
    for index, item in enumerate(surfaces):
        require(isinstance(item, dict), f"preflight.surfaces[{index}]: expected object")
        surface = identifier(
            item.get("surface"), f"preflight.surfaces[{index}].surface"
        )
        claim = identifier(item.get("claim"), f"preflight.surfaces[{index}].claim")
        require(surface in shot_list["surfaces"], f"{surface}: unknown surface")
        require(surface not in covered, f"duplicate preflight surface: {surface}")
        require(
            shot_list["surfaces"][surface]["claim"] == claim,
            f"{surface}: preflight claim does not match surface",
        )
        require(
            item.get("locatorCount") == 1,
            f"{surface}: locatorCount must be exactly 1",
        )
        require(item.get("visible") is True, f"{surface}: target is not visible")
        require(item.get("enabled") is True, f"{surface}: target is not enabled")
        validate_paint(item.get("paint"), f"preflight.surfaces[{index}].paint")
        covered.add(surface)
    expected = set(shot_list["surfaces"])
    require(
        covered == expected,
        "preflight surface mismatch; missing="
        + repr(sorted(expected - covered))
        + " extra="
        + repr(sorted(covered - expected)),
    )
    return shot_list, preflight


def probe(ffprobe: str, media: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,pix_fmt",
                "-of",
                "json",
                str(media),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise PreviewError(f"cannot probe {media}: {exc}") from exc


def video_info(ffprobe: str, media: Path) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
    info = probe(ffprobe, media)
    streams = info.get("streams", [])
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    require(len(videos) == 1, f"{media}: expected one video stream")
    try:
        duration = float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PreviewError(f"{media}: invalid duration") from exc
    require(math.isfinite(duration) and duration > 0, f"{media}: invalid duration")
    return videos[0], duration, streams


def load_recording(
    directory: Path, ffprobe: str
) -> tuple[dict[str, Any], dict[str, Any], Path, float]:
    shot_list = load_shot_list(directory)
    webms = sorted((directory / "video").glob("*.webm"))
    require(len(webms) == 1, f"expected one webm, got {len(webms)}")
    video, duration, _ = video_info(ffprobe, webms[0])
    require(
        (video.get("width"), video.get("height")) == (VIEW_W, VIEW_H),
        f"{webms[0]}: expected {VIEW_W}x{VIEW_H}",
    )

    workflow = read_json(directory / "workflow.json")
    nonempty(workflow.get("id"), "workflow.id")
    nonempty(workflow.get("title"), "workflow.title")
    steps = workflow.get("steps")
    require(isinstance(steps, list) and steps, "workflow.steps is empty")

    covered: set[str] = set()
    previous_end = 0.0
    for index, step in enumerate(steps):
        require(isinstance(step, dict), f"steps[{index}]: expected object")
        surface = identifier(step.get("surface"), f"steps[{index}].surface")
        claim = identifier(step.get("claim"), f"steps[{index}].claim")
        require(surface in shot_list["surfaces"], f"steps[{index}]: unknown surface")
        require(
            shot_list["surfaces"][surface]["claim"] == claim,
            f"steps[{index}]: claim does not match surface",
        )
        start = number(step.get("start"), f"steps[{index}].start")
        claim_time = number(step.get("time"), f"steps[{index}].time")
        end = number(step.get("end"), f"steps[{index}].end")
        require(0 <= start <= claim_time < end, f"steps[{index}]: bad time order")
        require(end <= duration + 0.05, f"steps[{index}]: end exceeds recording")
        require(
            start + 0.001 >= previous_end,
            f"steps[{index}]: clips overlap or descend",
        )
        if index == 0:
            require(start <= 1.0, "first clip must begin near capture start")
        description = nonempty(step.get("description"), f"steps[{index}].description")
        require(
            "\n" not in description and len(description.split()) <= 18,
            f"steps[{index}].description must be one clause of at most 18 words",
        )
        nonempty(step.get("action"), f"steps[{index}].action")
        nonempty(step.get("target"), f"steps[{index}].target")
        validate_paint(step.get("paint"), f"steps[{index}].paint")
        estimate = len(description.split()) / 2.5
        hold = end - claim_time
        require(
            abs(hold - estimate) <= 1.0,
            f"steps[{index}]: hold {hold:.2f}s vs speech estimate {estimate:.2f}s",
        )
        covered.add(surface)
        previous_end = end

    expected = set(shot_list["surfaces"])
    require(
        covered == expected,
        "workflow surface mismatch; missing="
        + repr(sorted(expected - covered))
        + " extra="
        + repr(sorted(covered - expected)),
    )
    return shot_list, workflow, webms[0], duration


def timeline(
    steps: list[dict[str, Any]],
    spoken_lengths: list[float],
) -> tuple[list[dict[str, Any]], float]:
    require(len(steps) == len(spoken_lengths), "speech/step count mismatch")
    cursor = LEAD_S
    items: list[dict[str, Any]] = []
    for index, (step, spoken) in enumerate(zip(steps, spoken_lengths)):
        pre = float(step["time"]) - float(step["start"])
        footage = float(step["end"]) - float(step["start"])
        piece = max(footage, pre + spoken)
        item = {
            "index": index,
            "surface": step["surface"],
            "claim": step["claim"],
            "description": step["description"],
            "sourceStart": float(step["start"]),
            "sourceEnd": float(step["end"]),
            "pieceStart": cursor,
            "pieceEnd": cursor + piece,
            "captionStart": cursor + pre,
            "captionEnd": cursor + pre + spoken,
            "pieceDuration": piece,
            "footageDuration": footage,
        }
        items.append(item)
        cursor += piece
        if index + 1 < len(steps):
            cursor += GAP_S
    return items, cursor + OUTRO_S


def write_render_review(
    directory: Path,
    mode: str,
    items: list[dict[str, Any]],
    duration: float,
) -> None:
    (directory / "render-review.json").write_text(
        json.dumps(
            {
                "mode": mode,
                "duration": duration,
                "lead": LEAD_S,
                "gap": GAP_S,
                "outro": OUTRO_S,
                "steps": items,
            },
            indent=2,
        )
        + "\n"
    )
