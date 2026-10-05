# Kit setup

Each tool is probed where it is first needed, so a run only checks what its
evidence uses:

| Need | When | Probes |
| --- | --- | --- |
| `capture` | first still or video | Playwright CLI + Chromium |
| `video` | a video was chosen | ffmpeg with libass, voice stack |
| `publish` | Publish | GitHub CLI |

```bash
python3 ~/.agents/skills/pr/scripts/check-kit.py <need> [<need> ...]
```

The JSON report caches a successful Chromium launch by Playwright CLI path and
version; use `--refresh` after repairing Chromium. `requiredReady: true`
completes the probe. Voice is optional. Use only the failed section below for
remediation, then rerun the probe.

## GitHub CLI

```bash
GH_VERSION=$(gh --version | awk 'NR==1 { print $3 }')
python3 -c 'import sys; v=tuple(map(int,sys.argv[1].split("."))); assert v >= (2,100,0), f"gh {sys.argv[1]} is older than 2.100.0"' "$GH_VERSION"
gh auth status
```

Missing: install via `brew install gh`, then `gh auth login`.
Done when: the comparison passes and auth reports logged in.

## Playwright CLI + Chromium

```bash
command -v playwright-cli
playwright-cli --version
playwright-cli -s=pr-kit open about:blank
playwright-cli -s=pr-kit close
```

Missing binary: stop and ask; a one-off `npx --version` is not a reusable
session command. Missing Chromium: `playwright-cli install-browser chromium`,
then repeat the launch check.
Done when: the installed binary launches and closes Chromium.

## ffmpeg with libass

Captions need an ffmpeg built with libass (`subtitles` filter). Ask the
same finder render uses (PATH, then common full builds):

```bash
python3 ~/.agents/skills/pr/scripts/build-pr-demo.py --print-ffmpeg
```

Missing: install such an ffmpeg — Homebrew `brew install ffmpeg-full`; on
Ubuntu and Debian the distro `ffmpeg` package carries libass.
`ffprobe` is the binary beside the path that printed.
Done when: the command prints a path.

## Voice stack

Narration is Kokoro-82M (voice `af_heart`) through kokoro-onnx, with misaki
turning text into phonemes and misaki's espeak-ng fallback for words outside
its dictionary. The same stack runs on macOS and on Linux with glibc 2.29 or
newer, x86_64 or arm64. Below that floor (RHEL/Rocky 8 is glibc 2.28) or on
musl (Alpine) the probe reports why and render falls back to a silent video
with a warning — never a stop.

Create the venv with a uv-managed Python 3.12, so the system Python's version
never matters. `--seed` adds pip, which misaki uses to fetch spaCy's English
model on its first run. No uv: install it per
<https://docs.astral.sh/uv/getting-started/installation/> (no sudo).

```bash
export PR_DEMO_TTS_VENV="${PR_DEMO_TTS_VENV:-$HOME/.local/share/pr-demo/tts-onnx-venv}"
UV_HTTP_TIMEOUT=600 uv venv --seed -p 3.12 "$PR_DEMO_TTS_VENV"
UV_HTTP_TIMEOUT=600 uv pip install -p "$PR_DEMO_TTS_VENV" kokoro-onnx soundfile "misaki[en]"
```

Download the pinned model files (~354MB from GitHub; slow links take
minutes). The probe verifies their SHA-256 against the pins in
`scripts/preview_common.py`:

```bash
export PR_DEMO_TTS_MODELS="${PR_DEMO_TTS_MODELS:-$HOME/.local/share/pr-demo/kokoro}"
mkdir -p "$PR_DEMO_TTS_MODELS"
base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
curl -fL -o "$PR_DEMO_TTS_MODELS/kokoro-v1.0.onnx" "$base/kokoro-v1.0.onnx"
curl -fL -o "$PR_DEMO_TTS_MODELS/voices-v1.0.bin" "$base/voices-v1.0.bin"
```

Warm the stack once, so record-time never downloads (the first run fetches
spaCy's English model, about 20s):

```bash
printf '["Voice kit ready."]' >"$TMPDIR/voice-check.json"
"$PR_DEMO_TTS_VENV/bin/python" ~/.agents/skills/pr/scripts/kokoro-tts.py \
  "$PR_DEMO_TTS_MODELS" "$TMPDIR/voice-check.json" "$TMPDIR/voice-check"
```

Done when: the warm-up writes `$TMPDIR/voice-check/beat-0.wav` and
`check-kit.py video` reports `voice.ready: true`. Default voice is `af_heart`
at speed 1.0; render takes per-run `--voice` and `--speed` overrides.
