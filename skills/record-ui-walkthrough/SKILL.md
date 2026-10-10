---
name: record-ui-walkthrough
description: "Records a captioned video walkthrough of a running web UI with Playwright: paced gestures, highlights on what each caption names, optional local voice-over, rendered with ffmpeg and checked frame by frame. Use when an interaction, motion, or multi-step flow needs a video because a still can't show it, for a PR, a design review, or a demo."
---

Record one short, paced video of a running web app that proves a few named claims, each one shown, highlighted, and captioned. The video is 1280×800 H.264, small enough to attach to a GitHub PR.

Work in a scratch dir outside the repo. A caller (the `pr` skill, say) may hand you one; otherwise use `SCRATCH="${TMPDIR:-/tmp}/walkthrough-<slug>"`. Skill files live at `~/.agents/skills/record-ui-walkthrough/`; expand `references/` and `scripts/` from there. The app must already be running and showing the state to record; starting it is the caller's job.

## Steps

1. **Probe.** Run `check-kit.py capture video` per [setup](references/setup.md).
   Done when: `requiredReady` is true. Voice is optional; a missing voice stack means a silent render.

2. **Shot list.** Write `$SCRATCH/shot-list.json` per [Shot list](#shot-list), then run `validate-video.py shots "$SCRATCH"`.
   Done when: the gate passes and every claim is something a viewer could see happen.

3. **Explore.** Open the session per [cli](references/cli.md#session), reach each surface, and confirm it is [served](#served). Generate a stable locator for every target.
   Done when: every surface is reachable and served, and every target has a locator from `generate-locator`.

4. **Preflight.** Dry-run every surface per [recording](references/recording.md#preflight).
   Done when: the preflight gate passes.

5. **Record.** Run the hero per [recording](references/recording.md#record), painting each beat per [highlight](references/highlight.md).
   Done when: the record gate passes and every review frame shows its claim, surface, and paint.

6. **Render and verify.** Per [recording](references/recording.md#render) and [verify](references/recording.md#verify).
   Done when: the render gate passes, every frame is reopened, and every speech window is played.

Hand back `$SCRATCH/walkthrough.mp4`, whether it is voiced or silent, and its duration.

## Shot list

```json
{
  "claims": [
    { "id": "short-claim", "description": "What visibly happens and why it matters." }
  ],
  "surfaces": [
    { "id": "stable-surface", "name": "Human-readable screen or section", "claim": "short-claim" }
  ]
}
```

IDs are unique, nonempty, and made of letters, digits, `.`, `_` and `-`. Every claim has at least one surface; each surface proves one claim. One surface per claim is the default; add another only when it shows something the first can't. The video walks the surfaces in order, one beat each.

## Served

Before recording a surface, check that the live page is running the code you mean to show. Look for a *fingerprint*: a class, computed style, or node that exists only in that code, or a spacing (gap, flush, overlap, offset) measured as a [relation](references/highlight.md#region-and-relation). Reload or open a fresh session to request it; the fingerprint is the bound, not a startup log or an HTTP 200. Dismiss any pointer interceptor that appears after a reload as part of this wait.
