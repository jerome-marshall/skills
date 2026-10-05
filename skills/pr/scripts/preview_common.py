"""Shared manifest, media, and timeline validation for the pr skill."""

from __future__ import annotations

import json
import math
import os
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
    """An invalid preview artifact."""


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


def nul_paths(path: Path) -> set[str]:
    try:
        parts = path.read_bytes().split(b"\0")
    except OSError as exc:
        raise PreviewError(f"{path}: {exc}") from exc
    return {os.fsdecode(part) for part in parts if part}


def load_scope(directory: Path, changed_paths: set[str]) -> dict[str, Any]:
    scope = read_json(directory / "scope.json")
    mode = nonempty(scope.get("mode"), "scope.mode")
    require(
        mode in {"stash", "branch", "sidecar", "pinned"},
        f"scope.mode: invalid mode {mode}",
    )
    nonempty(scope.get("default"), "scope.default")
    default_ref = nonempty(scope.get("defaultRef"), "scope.defaultRef")
    require(
        default_ref.startswith("refs/remotes/"),
        "scope.defaultRef must be a normalized remote ref",
    )
    dirty_paths = nul_paths(directory / "dirty.paths")
    if mode == "stash":
        require(dirty_paths == changed_paths, "stash changed paths must equal dirty paths")
    elif mode == "branch":
        require(not dirty_paths, "branch mode requires a clean tree")
    elif mode == "sidecar":
        require(bool(dirty_paths), "sidecar mode requires dirty paths")
        require(
            dirty_paths.isdisjoint(changed_paths),
            "sidecar dirty paths overlap the committed range",
        )
    else:
        preview_tree = Path(
            nonempty(scope.get("previewTree"), "scope.previewTree")
        ).resolve()
        require(preview_tree.is_dir(), f"pinned preview tree is missing: {preview_tree}")
        branch = identifier(scope.get("previewBranch"), "scope.previewBranch")
        require("/" not in branch, "pinned preview branch cannot contain '/'")
    return scope


def load_shot_list(directory: Path) -> dict[str, Any]:
    manifest = read_json(directory / "shot-list.json")
    claims = manifest.get("claims")
    groups = manifest.get("groups")
    path_coverage = manifest.get("pathCoverage")
    surfaces = manifest.get("surfaces")
    require(isinstance(claims, list) and claims, "shot-list.json: claims is empty")
    require(
        isinstance(groups, list) and groups,
        "shot-list.json: groups is empty",
    )
    require(
        isinstance(path_coverage, list) and path_coverage,
        "shot-list.json: pathCoverage is empty",
    )
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

    group_map: dict[str, dict[str, Any]] = {}
    grouped_claims: set[str] = set()
    for index, group in enumerate(groups):
        require(isinstance(group, dict), f"groups[{index}]: expected object")
        group_id = identifier(group.get("id"), f"groups[{index}].id")
        require(group_id not in group_map, f"duplicate group id: {group_id}")
        claim_id = identifier(group.get("claim"), f"groups[{index}].claim")
        require(claim_id in claim_map, f"{group_id}: unknown claim {claim_id}")
        nonempty(group.get("description"), f"groups[{index}].description")
        group_map[group_id] = group
        grouped_claims.add(claim_id)
    require(
        grouped_claims == set(claim_map),
        "claims without groups: " + repr(sorted(set(claim_map) - grouped_claims)),
    )

    changed_paths = nul_paths(directory / "changed.paths")
    require(changed_paths, "changed.paths is empty")
    covered_paths: set[str] = set()
    path_groups: set[str] = set()
    for index, item in enumerate(path_coverage):
        require(isinstance(item, dict), f"pathCoverage[{index}]: expected object")
        path = nonempty(item.get("path"), f"pathCoverage[{index}].path")
        require(path not in covered_paths, f"duplicate pathCoverage path: {path}")
        covered_paths.add(path)
        kind = nonempty(item.get("kind"), f"pathCoverage[{index}].kind")
        require(
            kind in {"visual", "behavioral", "inert"},
            f"pathCoverage[{index}].kind: invalid value {kind}",
        )
        item_groups = item.get("groups")
        if kind == "visual":
            require(
                isinstance(item_groups, list) and item_groups,
                f"pathCoverage[{index}].groups is empty",
            )
            seen_item_groups: set[str] = set()
            for group_index, value in enumerate(item_groups):
                group_id = identifier(
                    value, f"pathCoverage[{index}].groups[{group_index}]"
                )
                require(group_id in group_map, f"{path}: unknown group {group_id}")
                require(
                    group_id not in seen_item_groups,
                    f"{path}: duplicate group {group_id}",
                )
                seen_item_groups.add(group_id)
                path_groups.add(group_id)
        else:
            require(
                item_groups in (None, []),
                f"{path}: {kind} path cannot name groups",
            )
            nonempty(item.get("reason"), f"pathCoverage[{index}].reason")

    require(
        covered_paths == changed_paths,
        "shot-list path mismatch; missing="
        + repr(sorted(changed_paths - covered_paths))
        + " extra="
        + repr(sorted(covered_paths - changed_paths)),
    )
    require(
        path_groups == set(group_map),
        "groups without visual paths: " + repr(sorted(set(group_map) - path_groups)),
    )

    surface_map: dict[str, dict[str, Any]] = {}
    surfaced_groups: set[str] = set()
    for index, surface in enumerate(surfaces):
        require(isinstance(surface, dict), f"surfaces[{index}]: expected object")
        surface_id = identifier(surface.get("id"), f"surfaces[{index}].id")
        require(surface_id not in surface_map, f"duplicate surface id: {surface_id}")
        nonempty(surface.get("name"), f"surfaces[{index}].name")
        claim_id = identifier(surface.get("claim"), f"surfaces[{index}].claim")
        require(claim_id in claim_map, f"{surface_id}: unknown claim {claim_id}")
        surface_groups = surface.get("groups")
        require(
            isinstance(surface_groups, list) and surface_groups,
            f"{surface_id}: groups is empty",
        )
        seen_surface_groups: set[str] = set()
        for group_index, value in enumerate(surface_groups):
            group_id = identifier(value, f"{surface_id}.groups[{group_index}]")
            require(group_id in group_map, f"{surface_id}: unknown group {group_id}")
            require(
                group_map[group_id]["claim"] == claim_id,
                f"{surface_id}: group {group_id} has a different claim",
            )
            require(
                group_id not in seen_surface_groups,
                f"{surface_id}: duplicate group {group_id}",
            )
            seen_surface_groups.add(group_id)
            surfaced_groups.add(group_id)
        surface_map[surface_id] = surface

    require(
        surfaced_groups == set(group_map),
        "groups without representative surfaces: "
        + repr(sorted(set(group_map) - surfaced_groups)),
    )
    scope = load_scope(directory, changed_paths)
    return {
        "raw": manifest,
        "claims": claim_map,
        "groups": group_map,
        "path_coverage": path_coverage,
        "surfaces": surface_map,
        "changed_paths": changed_paths,
        "scope": scope,
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


def png_size(media: Path) -> tuple[int, int]:
    try:
        with media.open("rb") as handle:
            header = handle.read(24)
    except OSError as exc:
        raise PreviewError(f"{media}: {exc}") from exc
    require(
        len(header) == 24
        and header[:8] == b"\x89PNG\r\n\x1a\n"
        and header[12:16] == b"IHDR",
        f"{media}: expected a PNG",
    )
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


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
    nonempty(workflow.get("pr"), "workflow.pr")
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


def load_stills(directory: Path) -> list[dict[str, Any]]:
    shot_list = load_shot_list(directory)
    manifest = read_json(directory / "stills.json")
    pairs = manifest.get("pairs")
    require(isinstance(pairs, list) and pairs, "stills.pairs is empty")
    seen: set[str] = set()
    for index, pair in enumerate(pairs):
        require(isinstance(pair, dict), f"pairs[{index}]: expected object")
        claim = identifier(pair.get("claim"), f"pairs[{index}].claim")
        require(claim in shot_list["claims"], f"pairs[{index}]: unknown claim")
        require(claim not in seen, f"duplicate still pair for claim {claim}")
        seen.add(claim)
        for state in ("before", "after"):
            filename = nonempty(pair.get(state), f"pairs[{index}].{state}")
            path = (directory / filename).resolve()
            require(
                path.is_relative_to(directory.resolve()),
                f"pairs[{index}].{state}: path leaves scratch",
            )
            require(path.is_file(), f"missing still: {path}")
            require(
                png_size(path) == (VIEW_W, VIEW_H),
                f"{path}: expected {VIEW_W}x{VIEW_H}",
            )
    require(seen == set(shot_list["claims"]), "stills must cover every claim once")
    return pairs


def load_runs(directory: Path) -> list[dict[str, Any]]:
    manifest = read_json(directory / "runs.json")
    runs = manifest.get("runs")
    require(isinstance(runs, list) and runs, "runs.json: runs is empty")
    seen: set[str] = set()
    for index, run in enumerate(runs):
        label = f"runs[{index}]"
        require(isinstance(run, dict), f"{label}: expected object")
        claim = identifier(run.get("claim"), f"{label}.claim")
        require(claim not in seen, f"duplicate run for claim {claim}")
        seen.add(claim)
        nonempty(run.get("description"), f"{label}.description")
        nonempty(run.get("command"), f"{label}.command")
        kind = nonempty(run.get("kind"), f"{label}.kind")
        require(kind in {"test", "output"}, f"{label}.kind: invalid value {kind}")
        logs: dict[str, bytes] = {}
        exits: dict[str, int] = {}
        for state in ("before", "after"):
            side = run.get(state)
            require(isinstance(side, dict), f"{label}.{state}: expected object")
            path = (directory / nonempty(side.get("log"), f"{label}.{state}.log")).resolve()
            require(
                path.is_relative_to(directory.resolve()),
                f"{label}.{state}.log: path leaves scratch",
            )
            require(path.is_file(), f"missing log: {path}")
            logs[state] = path.read_bytes()
            exit_path = path.with_suffix(".exit")
            try:
                exits[state] = int(exit_path.read_text().strip())
            except (OSError, ValueError) as exc:
                raise PreviewError(f"{exit_path}: expected an exit code") from exc
        if kind == "test":
            require(exits["before"] != 0, f"{claim}: test is not red on the before tree")
            require(exits["after"] == 0, f"{claim}: test is not green on the after tree")
        else:
            require(exits["after"] == 0, f"{claim}: command failed on the after tree")
            require(logs["before"] != logs["after"], f"{claim}: before and after output match")
    return runs
