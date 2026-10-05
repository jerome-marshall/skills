# Before/after

How to fix the change range, cover every claim, and capture stills and runs
on the after tree and the before tree inside one window. Stash, branch, and
sidecar use the current served tree. Pinned uses one isolated
default-plus-pin worktree for capture and publication.

## Which path

Normalize the default branch once:

```bash
DEFAULT=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD)
DEFAULT=${DEFAULT#origin/}
if test -z "$DEFAULT"; then
  DEFAULT=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)
fi
DEFAULT_REF="refs/remotes/origin/$DEFAULT"
git fetch origin "+refs/heads/$DEFAULT:$DEFAULT_REF"
```

`$changed` is the NUL-delimited `$SCRATCH/changed.paths`; status is the
NUL-delimited `$SCRATCH/opening.status`. Paths never pass through shell word
splitting. Snapshot the tree first — this is the Scope snapshot every restore
compares against:

```bash
git status --porcelain=v1 -z >"$SCRATCH/opening.status"
git rev-parse HEAD >"$SCRATCH/opening.head"
git diff --name-only -z HEAD >"$SCRATCH/dirty.paths"
git ls-files --others --exclude-standard -z >>"$SCRATCH/dirty.paths"
```

**Pinned.** The user named a SHA. Resolve it (`git rev-parse`); failure
is a stop. Merge commits are a stop. Create the capture tree from the remote
default, then cherry-pick the pin:

```bash
pin=$(git rev-parse --verify "$USER_SHA^{commit}")
test "$(git rev-list --parents -n 1 "$pin" | wc -w | tr -d ' ')" = 2
git diff --name-only -z "$pin^" "$pin" >"$SCRATCH/changed.paths"
short=$(git rev-parse --short=12 "$pin")
PREVIEW_TREE="${TMPDIR:-/tmp}/pr-tree-$short-$$"
PREVIEW_BRANCH="pr-$short-$$"
git worktree add -b "$PREVIEW_BRANCH" "$PREVIEW_TREE" "$DEFAULT_REF"
git -C "$PREVIEW_TREE" cherry-pick "$pin"
git -C "$PREVIEW_TREE" rev-parse HEAD >"$SCRATCH/preview.head"
```

Cherry-pick conflict: abort it, remove the preview worktree and branch, then
stop. Pinned runs, dev servers, and publication all use `$PREVIEW_TREE`.

**No named SHA.** Compute the committed range and dirty paths:

```bash
base=$(git merge-base HEAD "$DEFAULT_REF")
ahead=$(git rev-list --count "$base"..HEAD)
git diff --name-only -z "$base" HEAD >"$SCRATCH/changed.paths"
```

When `ahead > 0`, clean is **branch**. Dirty is **sidecar** only when its
tracked and untracked path set is disjoint from `changed.paths`; compare the
two NUL-delimited files as path sets. Overlap is **mixed** — stop.

**Stash.** No named SHA, `ahead` is zero, and the tree is dirty. Build
`changed.paths` from tracked and untracked dirt:

```bash
git diff --name-only -z HEAD >"$SCRATCH/changed.paths"
git ls-files --others --exclude-standard -z >>"$SCRATCH/changed.paths"
```

An existing stash is a stop. Clean with `ahead == 0`, an empty
`changed.paths`, or an empty commit range is a stop. Say which path the
capture covers before changing the tree.

Write `$SCRATCH/scope.json` with the selected mode and normalized refs:

```json
{
  "mode": "stash|branch|sidecar|pinned",
  "default": "main",
  "defaultRef": "refs/remotes/origin/main",
  "base": "resolved merge base or null",
  "previewTree": "absolute pinned worktree path or null",
  "previewBranch": "pinned branch name or null"
}
```

Run the scope gate. With a `shot-list.json` it checks coverage too; without
one it checks `scope.json` against `changed.paths`:

```bash
python3 ~/.agents/skills/pr/scripts/validate-pr.py scope "$SCRATCH"
```

## Serving

Visual claims need a dev URL that serves the tree under capture (pinned:
`$PREVIEW_TREE`). Reuse a supplied URL only when its **fingerprint** matches
that tree (see [Claim](#claim)). Otherwise start the repository's known
noninteractive dev command from that tree on a free port. Preserve every
existing server. Ask only when startup needs user-only interaction or secrets.
The entry URL opens the app; the shot list defines coverage.

## Coverage

Visual paths need a shot list. Separate **path accounting** from **visual
proof**. Every path in `$changed` gets its Scope kind. Group visual paths by
behavior: paths belong to the same group only when one representative
interaction proves the same claim for all of them. Distinct component
variants, states, or interactions use distinct groups.

The **shot list** contains one representative surface per group. More
surfaces are allowed when they add evidence; repeated hosts of the same
behavior are not required. A shared component maps to the group it actually
renders, never to a convenient unrelated screen. Ask the user for surfaces only
when source and routes cannot identify a representative.

Write `$SCRATCH/shot-list.json`:

```json
{
  "claims": [
    { "id": "short-claim", "description": "What visibly changes and why." }
  ],
  "groups": [
    {
      "id": "behavior-variant",
      "claim": "short-claim",
      "description": "Equivalent implementation and interaction being sampled."
    }
  ],
  "pathCoverage": [
    {
      "path": "src/Component.jsx",
      "kind": "visual",
      "groups": ["behavior-variant"]
    },
    {
      "path": "src/api/routes.ts",
      "kind": "behavioral",
      "reason": "Proved by the tags-filter run."
    },
    {
      "path": "src/messages.json",
      "kind": "inert",
      "reason": "End-of-file newline only."
    }
  ],
  "surfaces": [
    {
      "id": "stable-surface",
      "name": "Human-readable screen or section",
      "claim": "short-claim",
      "groups": ["behavior-variant"]
    }
  ]
}
```

IDs are unique nonempty strings. Every path in `changed.paths` appears exactly
once in `pathCoverage`. Visual paths name one or more existing groups;
behavioral and inert paths carry a concrete reason and no groups. Every group
has visual paths and at least one representative surface. A surface's groups
all share its claim.

**Video** walks the representative surface list: each surface is a recorded
prove, and every behavior group is represented.

**Stills** are one before/after pair per visual **claim**. The same claim on
many surfaces is one pair — shoot the first surface that shows it. A second
pair only when the claim itself differs.

Done when: the scope gate passes with the shot list, every changed path is
classified, and every behavior group has a representative surface.

## Claim

A still is ready when the tree is **served**, the claim is **visible**, and
the pair shares **chrome**.

**Served.** The live page carries a *fingerprint* of the tree on disk — a
class, computed style, or node that exists only in that tree, or a
**spacing** (gap, flush, overlap, offset): the
[relation measurement](highlight.md) between the two visual pieces. Reload or a
fresh session is how you request it; the fingerprint is the bound. A pointer
interceptor that appears after the tree change is dismissed as part of this
wait.

**Visible.** The defect is on screen in the before tree, the fix in the after
tree. A claim that is only true after a gesture (scroll, overflow, sticky
chrome, hover) uses that same gesture before the shot — the PNG is the
acted surface.

**Chrome.** The pair shares the rest of the product frame (banners, nav,
selection, and focus). Stills come from a fresh page which never ran recording
helpers. After reload, restore the after still's chrome, then open the claim.
Replace a still only when the new frame still shows the claim, chrome matches,
and no recording paint, locator miss, loading state, error surface, or
incidental overlay is visible.

Screenshots use the [cli](cli.md) session at the 1280×800 viewport:
`screenshot --filename=$SCRATCH/<slug>-after.png`. `<slug>` is the claim id,
shared with the body.

## Runs

A behavioral claim is proved by one command that goes **red** on the before
tree and **green** on the after tree.

- **test** — the narrowest existing test that covers the claim, run through
  the repo's own test script with a filter. Red is a failing assertion about
  the claim; a compile, import, or setup error is not red.
- **output** — when no test covers the claim: a command whose output shows it
  (a request to the route, a script, a CLI call). Red and green are the two
  outputs differing in the line that carries the claim. Offer a regression
  test during Review.

Test files the run needs are **kept paths**: they stay at their after state
inside the window, so a test the PR adds still exists on the before tree.
List them NUL-delimited in `$SCRATCH/kept.paths` (empty when none), then
derive the paths the window reverts:

```bash
python3 - "$SCRATCH" <<'EOF'
import sys
from pathlib import Path
d = Path(sys.argv[1])
def read(name):
    p = d / name
    return [x for x in p.read_bytes().split(b"\0") if x] if p.exists() else []
kept = set(read("kept.paths"))
(d / "before.paths").write_bytes(
    b"".join(x + b"\0" for x in read("changed.paths") if x not in kept)
)
EOF
```

Capture each run from the tree under capture. The log holds stdout and
stderr; the exit code lands beside it and the gate reads it from there:

```bash
mkdir -p "$SCRATCH/runs"
<command> >"$SCRATCH/runs/<claim>-after.log" 2>&1
echo $? >"$SCRATCH/runs/<claim>-after.exit"
```

Write `$SCRATCH/runs.json`:

```json
{
  "runs": [
    {
      "claim": "short-claim",
      "description": "What the run proves.",
      "kind": "test|output",
      "command": "pnpm turbo run test --filter=web -- tags-filter",
      "before": { "log": "runs/short-claim-before.log" },
      "after": { "log": "runs/short-claim-after.log" }
    }
  ]
}
```

```bash
python3 ~/.agents/skills/pr/scripts/validate-pr.py runs "$SCRATCH"
```

Then read both logs: red names the claim's assertion or output line, green
shows it holding.

## Window

One window captures every still and run. After-first:

1. Scope already saved exact NUL status and `HEAD`. Pinned also saved the
   isolated preview `HEAD`.
2. On the after tree: on a fresh screenshot page, confirm each visual claim,
   then shoot `<scratch>/<slug>-after.png`. Run each behavioral command into
   its `-after` log.
3. Materialize before (stash, branch, sidecar, or pinned below), reverting
   `before.paths`.
4. On the before tree: confirm the before fingerprint is served, restore the
   after still's chrome, confirm the claim, then shoot
   `<scratch>/<slug>-before.png`. Run each behavioral command into its
   `-before` log.
5. Restore.
6. Write and validate `$SCRATCH/stills.json` and `$SCRATCH/runs.json`, then
   reopen every PNG at full size and read every log:

```json
{
  "pairs": [
    {
      "claim": "short-claim",
      "before": "short-claim-before.png",
      "after": "short-claim-after.png"
    }
  ]
}
```

7. Recreate status as NUL-delimited bytes and compare it with
   `opening.status`; compare `HEAD` with `opening.head`. Pinned compares the
   isolated tree with `preview.head` and confirms the user's tree still matches
   both opening files.

```bash
git status --porcelain=v1 -z >"$SCRATCH/restored.status"
git rev-parse HEAD >"$SCRATCH/restored.head"
cmp "$SCRATCH/opening.status" "$SCRATCH/restored.status"
cmp "$SCRATCH/opening.head" "$SCRATCH/restored.head"
python3 ~/.agents/skills/pr/scripts/validate-pr.py stills "$SCRATCH"
python3 ~/.agents/skills/pr/scripts/validate-pr.py runs "$SCRATCH"
```

Run only the gates for the evidence the PR has.

Done when: each visual claim has one before/after PNG pair that shows the
correct state and target, shares chrome, and carries no recording paint or
incidental artifact; each behavioral claim has a red before log and a green
after log; and the repo matches the Scope snapshot.

## Stash

Materialize with one identifiable stash of `before.paths`:

```bash
GIT_LITERAL_PATHSPECS=1 git stash push -u -m "pr-$PPID" \
  --pathspec-from-file="$SCRATCH/before.paths" --pathspec-file-nul
STASH_OID=$(git rev-parse refs/stash)
```

Restore staging and worktree state with `git stash apply --index "$STASH_OID"`.
Recreate status and require a byte match before dropping anything. Confirm
`refs/stash` is still `$STASH_OID`, then `git stash drop stash@{0}`. A failed
apply or mismatch stops with the stash retained.

## Branch and sidecar

Create one full binary patch of `before.paths`:

```bash
GIT_LITERAL_PATHSPECS=1 xargs -0 -r git diff --binary --full-index \
  "$base" HEAD -- <"$SCRATCH/before.paths" >"$SCRATCH/after.patch"
git apply --check --reverse --index "$SCRATCH/after.patch"
git apply --reverse --index "$SCRATCH/after.patch"
```

This changes only paths in the committed range; disjoint sidecar paths and
their index state remain untouched. Restore with `git apply --check --index`
then `git apply --index`. Recreate NUL status and require byte equality. A
failed `--check` is a stop before mutation.

## Pinned

Operate only in `$PREVIEW_TREE`. Build `after.patch` from its cherry-picked
commit, then use the same reverse/apply sequence as Branch:

```bash
publish_head=$(cat "$SCRATCH/preview.head")
GIT_LITERAL_PATHSPECS=1 xargs -0 -r git -C "$PREVIEW_TREE" diff --binary --full-index \
  "$publish_head^" "$publish_head" -- \
  <"$SCRATCH/before.paths" >"$SCRATCH/after.patch"
git -C "$PREVIEW_TREE" apply --check --reverse --index "$SCRATCH/after.patch"
git -C "$PREVIEW_TREE" apply --reverse --index "$SCRATCH/after.patch"
```

Restore with checked forward `git apply --index`. Require a clean preview tree
at `preview.head`; separately require the user's worktree status and `HEAD` to
match the opening files.

## On failure

Stop and hand control back. Preserve the exact stash or patch and report its
path. The user owns recovery — no auto-resolve, no stash drop after a mismatch,
and no whole-tree reset or sequencer abort.
