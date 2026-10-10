# CLI session

Same `playwright-cli` binary the `capture` probe checked. Prefix every call with `-s=walkthrough`.
Command names live in `playwright-cli --help`; this file carries the
conventions `--help` does not.

## Session

Write `$SCRATCH/cli.config.json`:

```json
{
  "browser": {
    "browserName": "chromium",
    "contextOptions": {
      "ignoreHTTPSErrors": true,
      "viewport": { "width": 1280, "height": 800 }
    }
  },
  "outputDir": "<absolute $SCRATCH>"
}
```

`outputDir` is where `.playwright-cli/` snapshots land — scratch, not the
app repo. Equivalents: `PLAYWRIGHT_MCP_IGNORE_HTTPS_ERRORS`,
`PLAYWRIGHT_MCP_VIEWPORT_SIZE=1280x800`,
`PLAYWRIGHT_MCP_OUTPUT_DIR`,
`PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=1` (scratch writes under
`$TMPDIR`). Action timeout defaults to 5s; dismiss pointer interceptors
first, then raise `PLAYWRIGHT_MCP_TIMEOUT_ACTION` if the page is still
settling. CLI `click` has no force flag.

Each `playwright-cli` invocation assigns `SCRATCH` and exports
`PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=1` in that command.
`--filename` values are `$SCRATCH/...`.

```bash
SCRATCH=<the scratch dir from SKILL.md>
export PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=1
playwright-cli -s=walkthrough open --config="$SCRATCH/cli.config.json" "$URL"
playwright-cli -s=walkthrough resize 1280 800
```

Resize when the window does not match the viewport. Close with
`playwright-cli -s=walkthrough close`.

## Explore

Routing, login, and row-picking stay CLI. After the first snapshot, prefer:

- `find "Label"` (or `--regex`) when the tree is large
- `snapshot --depth=N` or `snapshot eN` for a region (the dialog, a form)
- `snapshot --filename=$SCRATCH/tree.yml` when the full tree belongs on disk
- `--raw` on `click` / `fill` / `press` once the target is known
- `click "getByRole('button', { name: 'Submit' })"` when the name is known
- `eval` for [served](../SKILL.md#served) fingerprints; `eval --filename` for
  large results

A full in-chat snapshot is for a small surface. For each hero beat,
`playwright-cli -s=walkthrough --raw generate-locator eN` — those locators go
in the hero; snapshot refs expire.

## Preflight

Run the generated dry-run before the hero:

```bash
playwright-cli -s=walkthrough --raw run-code \
  --filename="$SCRATCH/preflight.js" >"$SCRATCH/preflight.json"
python3 -m json.tool "$SCRATCH/preflight.json" >/dev/null
python3 ~/.agents/skills/record-ui-walkthrough/scripts/validate-video.py preflight "$SCRATCH"
rm -rf "$SCRATCH/video"
```

The preflight reaches every shot-list surface with the same routes,
setup actions, locators, and claim measurements as `hero.js`. It also clears a
stale screencast and proves that a new screencast can start and stop.

## Hero

Write `$SCRATCH/hero.js` with Python (or a heredoc that already contains the
expanded `$SCRATCH` path). `path` is the absolute
`$SCRATCH/video/walkthrough.webm` string. Confirm `hero.js` contains a path under
`$TMPDIR` before `run-code`. Waits inside `run-code` are
`page.waitForTimeout`. The hero uses only its `page` parameter. Navigate that
page to every shot-list surface after capture starts; pages opened during
exploration are not part of its screencast.

```js
async page => {
  const steps = [];
  let recording = false;
  let t0 = 0;
  const now = () => (Date.now() - t0) / 1000;
  try {
    await page.screencast.start({
      path: "/abs/scratch/video/walkthrough.webm",
      size: { width: 1280, height: 800 }
    });
    recording = true;
    t0 = Date.now();

    // For each shot-list surface:
    // const start = now(); perform the visible prove; paint the exact claim;
    // const time = now(); hold for the line; const end = now();
    // steps.push({
    //   surface, claim, start, time, end, action, target, paint, description
    // });
    // clearHighlights(page), then navigate this page to the next surface.
  } finally {
    await clearHighlights(page);
    if (recording) await page.screencast.stop();
  }
  return {
    id: "stable-walkthrough-id",
    title: "Walkthrough title",
    steps
  };
}
```

```bash
playwright-cli -s=walkthrough --raw run-code \
  --filename="$SCRATCH/hero.js" >"$SCRATCH/workflow.json"
python3 -m json.tool "$SCRATCH/workflow.json" >/dev/null
```

The file is one function expression, `async page => { ... }`. The CLI wraps
and evaluates it. Redirect the returned value; never reconstruct timestamps or
steps by hand. Each step's `surface` and `claim` match `shot-list.json`.
`start` begins the footage worth keeping, `time` is when the painted claim is
visible and speech may start, and `end` follows the hold. Use locators from
`generate-locator`, not snapshot refs. Keep the function to the paced
walkthrough — explore stays CLI.
