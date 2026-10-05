# Record, render, verify

The video branch, run on the after tree before the stills window: Preflight,
Record, Render, Verify. Probe `check-kit.py capture video` per
[setup](setup.md) first.

One named `@playwright/cli` session. Explore with snapshots and refs; the
paced walkthrough is one hero script via `run-code` + `page.screencast`.
Viewport and screencast size are **1280×800**. Session, config, explore, and
the hero invoke: [cli](cli.md).

## Recorder

Launch Chromium through the CLI per [cli](cli.md). A pointer interceptor
(dev-server error iframe, cookie banner) is dismissed — or `force`d only
after it is identified — before the hero runs.

Fallback, only if that CLI cannot launch: Playwright **library** in scratch
(`chromium.launch` + `page.screencast`). Same viewport, same hero shape.

## Cold-open

Start `page.screencast` after the first shot-list surface is up. Routing,
login, row-picking, and interceptor dismiss before the first prove stay
off-camera. For later surfaces, navigate the recorded `page`; put travel
outside every step's `start..end` clip so render removes it. Every destination
and prove still occurs after capture starts. Setup clicks get no captions,
chapters, or highlights.

## Prove

The claim is only true after the user acts (scroll, overflow, sticky chrome,
drag, hover, empty vs filled). That action is a beat. Drive the same gesture
a human would (wheel, drag, hover) over enough frames that content *moves*
on video. A still of the after-state is not the proof. Each shot-list
surface gets that prove: mark `start`, perform the action, mark `time` when
the painted claim is on screen, hold, then mark `end`.

## Preflight

Write `$SCRATCH/preflight.js` as the no-footage twin of `hero.js`. It uses the
same routes, setup actions, locators, and geometry helpers. For every
representative surface it:

1. reaches the intended state;
2. requires the target locator count to equal one;
3. requires the target to be visible and enabled;
4. performs the prove and measures its paint; and
5. clears highlights before moving on.

Before those checks, stop a stale screencast in a guarded `try`, then
start/stop a short `$SCRATCH/video/preflight.webm` probe. Return
`screencastReady: true` only after that probe succeeds. The returned object is:

```json
{
  "screencastReady": true,
  "errors": [],
  "surfaces": [
    {
      "surface": "shot-list surface id",
      "claim": "shot-list claim id",
      "locatorCount": 1,
      "visible": true,
      "enabled": true,
      "paint": { "kind": "relation", "axis": "vertical", "order": "a-before-b", "state": "gap", "distance": 5 }
    }
  ]
}
```

Capture the actual return value as `$SCRATCH/preflight.json`, then run:

```bash
python3 ~/.agents/skills/pr/scripts/validate-pr.py preflight "$SCRATCH"
```

Delete `$SCRATCH/video/` after this gate passes. A failed preflight repairs the
route, state, or locator before any hero recording starts. Reconcile every
preflight locator and setup action with `hero.js`; the passing dry run is not
permission to substitute different recording logic.

Done when: preflight coverage equals the shot list; every target resolves
once, is enabled, and proves the claim; and `screencastReady` is true.

## Record

Paint each beat per [highlight](highlight.md) (node, region, relation).
Before recording, reopen `hero.js` and reconcile it with the passing preflight
and `shot-list.json`. The hero uses its one `page`; other tabs are
exploration, not footage.

Empty `<scratch>/video/` before `page.screencast.start`. Write one file:
`<scratch>/video/pr-demo.webm`.

Assign `t0 = Date.now()` on the next line after `screencast.start` returns.
`t0` and capture start are the same instant.

Each beat returns:

```json
{
  "surface": "shot-list surface id",
  "claim": "shot-list claim id",
  "start": 0.1,
  "time": 0.8,
  "end": 4.2,
  "action": "open",
  "target": "Actions",
  "paint": {
    "kind": "relation",
    "axis": "vertical",
    "order": "a-before-b",
    "state": "gap",
    "distance": 5
  },
  "description": "The menu now has the intended gap."
}
```

`start` is immediately before the visible prove, `time` is when its exact
painted claim is on screen, and `end` follows the spoken-length hold. Times use
the capture clock and obey `0 <= start <= time < end <= webm duration`; clips
are ordered and non-overlapping. `paint.kind` is `node`, `region`, `relation`,
or `none`; relation paint records the validated geometry returned by
`highlightRelation`. `none` carries a reason. `description` is one nonempty
short clause of at most 18 words, burned and spoken.

Redirect the hero's actual return value to `workflow.json` per
[cli](cli.md). Then run:

```bash
python3 ~/.agents/skills/pr/scripts/validate-pr.py record "$SCRATCH"
```

This validates both manifests and timing, checks exact shot-list coverage, and
writes one raw-webm frame at each claim time to
`$SCRATCH/review/record-<surface>-<n>.png`. Reopen `hero.js`,
`workflow.json`, and every review frame. Fail Record when any surface is
missing, metadata differs from the source, paint misses its caption class, the
claim is absent, or the hold differs from estimated speech by more than about
one second.

Done when: scratch has one `.webm`; the manifests validate; workflow coverage
equals the representative shot list; every clip has ordered start, claim, and
end times; and every review frame shows the named claim, surface, and paint.

## Chapters

`showChapter` stays available, **off by default**. Use it when the pause *is*
the point (new-screen intro; before/after smash in one take; multi-surface
title card).

## Render

Execute, do not rewrite:

```bash
python3 ~/.agents/skills/pr/scripts/build-pr-demo-with-voice.py "$SCRATCH"
```

Voice is default. The script validates first, synthesizes each beat's
`description` with the local Kokoro voice (`af_heart`, override with
`--voice`), then rebuilds the timeline from explicit `start..end` clips with
the audio in charge. Travel outside clips is removed; each caption starts at
the beat's `time`, spans that line exactly, and overruns hold the last frame
(motion is never retimed). Timeline: 0.3s lead-in, 0.4s gaps, 0.8s outro.
Reads the single `<scratch>/video/*.webm` (1280×800) plus both manifests.
Writes `<scratch>/demo.ass`, `<scratch>/voice/` audio,
`<scratch>/pr-demo.mp4`, and `<scratch>/render-review.json`.

Fallback: only a missing or broken voice stack (or a host below the voice floor in [setup](setup.md#voice-stack)) warns on
stderr and renders the silent video via `build-pr-demo.py`. Invalid or missing
preview inputs are hard failures. Both paths use the same output names; the
Review says which mode ran.

The silent path uses the same explicit clips, estimates caption length at 2.5
words/second, and freezes only when a line outlasts its clip. PlayRes matches
the 1280×800 viewport.

Both need an ffmpeg with libass (`subtitles` filter); the same finder as
[setup](setup.md) (`--print-ffmpeg`). If none: per setup.

## Verify

```bash
python3 ~/.agents/skills/pr/scripts/validate-pr.py render "$SCRATCH"
```

The validator checks H.264 / `yuv420p`, 1280×800, duration, stream mode, and
caption windows from `render-review.json`; it emits one midpoint frame per
caption to `$SCRATCH/review/render-<surface>-<n>.png`.

Done when: every frame is reopened and every speech window played; paint
matches its caption class; the correct claim and surface are visible; voiced
output has real speech in each caption window and silence in declared gaps;
silent fallback has no audio; and the file is under the limits below.

## Limits

GitHub attachments: 10MB per image; 10MB video on Free, 100MB on paid. A 30s
800p H.264 cut is well under a megabyte. If the mp4 approaches 10MB, shorten
or re-encode before Review.
