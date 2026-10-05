#!/usr/bin/env python3
"""Probe the pr toolchain in one command."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import preview_common as common

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "pr" / "kit.json"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def load_cache() -> dict[str, Any]:
    try:
        value = json.loads(CACHE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_cache(value: dict[str, Any]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(value, indent=2) + "\n")


def check_gh() -> dict[str, Any]:
    binary = shutil.which("gh")
    if not binary:
        return {"ready": False, "action": "Install GitHub CLI 2.100.0 or newer."}
    version_result = run([binary, "--version"])
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version_result.stdout)
    version = match.group(0) if match else None
    recent = bool(match and tuple(map(int, match.groups())) >= (2, 100, 0))
    auth = run([binary, "auth", "status"])
    ready = version_result.returncode == 0 and recent and auth.returncode == 0
    result: dict[str, Any] = {
        "ready": ready,
        "binary": binary,
        "version": version,
        "authenticated": auth.returncode == 0,
    }
    if not ready:
        result["action"] = (
            "Upgrade gh to 2.100.0 or newer and run `gh auth login`."
        )
    return result


def check_playwright(cache: dict[str, Any], refresh: bool) -> dict[str, Any]:
    binary = shutil.which("playwright-cli")
    if not binary:
        return {"ready": False, "action": "Install the playwright-cli binary."}
    version_result = run([binary, "--version"])
    version = version_result.stdout.strip()
    cache_key = {"binary": str(Path(binary).resolve()), "version": version}
    cached = (
        not refresh
        and version_result.returncode == 0
        and cache.get("playwright") == cache_key
    )
    if cached:
        return {**cache_key, "ready": True, "browserLaunch": "cached"}

    run([binary, "-s=pr-kit", "close"])
    launched = run([binary, "-s=pr-kit", "open", "about:blank"])
    closed = run([binary, "-s=pr-kit", "close"])
    ready = (
        version_result.returncode == 0
        and launched.returncode == 0
        and closed.returncode == 0
    )
    result: dict[str, Any] = {
        **cache_key,
        "ready": ready,
        "browserLaunch": "checked",
    }
    if ready:
        cache["playwright"] = cache_key
    else:
        result["action"] = (
            "Run `playwright-cli install-browser chromium`, then retry."
        )
        result["detail"] = (launched.stderr or launched.stdout).strip()
    return result


def check_video() -> dict[str, Any]:
    result = run([sys.executable, str(HERE / "build-pr-demo.py"), "--print-ffmpeg"])
    ready = result.returncode == 0 and bool(result.stdout.strip())
    value: dict[str, Any] = {
        "ready": ready,
        "ffmpeg": result.stdout.strip() or None,
    }
    if not ready:
        value["action"] = "Install ffmpeg with the libass subtitles filter."
        value["detail"] = result.stderr.strip()
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_models(cache: dict[str, Any], root: Path) -> bool:
    verified = cache.setdefault("voiceModels", {})
    for name, expected in common.VOICE_MODEL_FILES.items():
        path = root / name
        if not path.is_file():
            return False
        stat = path.stat()
        key = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
        if verified.get(name) == key:
            continue
        if sha256(path) != expected:
            return False
        verified[name] = key
    return True


def check_voice(cache: dict[str, Any]) -> dict[str, Any]:
    unsupported = common.voice_unsupported()
    if unsupported:
        return {"ready": False, "optional": True, "reason": unsupported}
    venv = Path(os.environ.get("PR_DEMO_TTS_VENV", str(common.VOICE_VENV_DEFAULT)))
    models = Path(os.environ.get("PR_DEMO_TTS_MODELS", str(common.VOICE_MODELS_DEFAULT)))
    python = venv / "bin" / "python"
    loaded = (
        run(
            [
                str(python),
                "-c",
                "import kokoro_onnx, soundfile; from misaki import en, espeak; "
                "espeak.EspeakFallback(british=False)",
            ]
        ).returncode
        == 0
        if python.is_file()
        else False
    )
    weights = check_models(cache, models)
    ready = loaded and weights
    result: dict[str, Any] = {
        "ready": ready,
        "optional": True,
        "venv": str(venv),
        "models": str(models),
        "stack": loaded,
        "weights": weights,
    }
    if not ready:
        result["action"] = "Complete the voice setup in references/setup.md."
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("needs", nargs="+", choices=("capture", "video", "publish"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    cache = load_cache()
    report: dict[str, Any] = {}
    if "capture" in args.needs:
        report["playwright"] = check_playwright(cache, args.refresh)
    if "video" in args.needs:
        report["video"] = check_video()
        report["voice"] = check_voice(cache)
    if "publish" in args.needs:
        report["gh"] = check_gh()
    save_cache(cache)
    required_ready = all(
        section["ready"] for section in report.values() if not section.get("optional")
    )
    report["requiredReady"] = required_ready
    print(json.dumps(report, indent=2))
    return 0 if required_ready else 1


if __name__ == "__main__":
    sys.exit(main())
