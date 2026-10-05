# Review and publish

How the draft reaches the user, and how it reaches GitHub once they approve.
Media stays in scratch, off the branch; `gh --attach` uploads it.

## Review

First delete the app-repo `.playwright-cli/` this session wrote (CLI
snapshots and logs). Then reply with, in order:

1. One or two sentences: what changed and what the evidence shows.
2. The title, in a code span.
3. The full `body.md`, verbatim as markdown — absolute `$SCRATCH` paths make
   the stills render inline.
4. `Video: <absolute path to pr-demo.mp4>` when it exists; otherwise
   `No video was needed, so none was created.` on visual PRs.
5. When a PR already exists (`gh pr view --json number,url,title,body`), its
   current title and description under **Replaces**, since Publish overwrites
   both.
6. Offers the user can take: a regression test for each claim proved by
   output instead of a test; anything marked uncertain.

End the turn there. A revision returns to the step it touches and reruns that
step's gate, then presents the full review again. Publish waits for one
explicit go-ahead that covers commit, push, and PR.

## Publish

Run `check-kit.py publish` per [setup](setup.md). Run `gh` from the publish
repo: `$PREVIEW_TREE` for pinned, the app repo root otherwise.

**Commit and push**, by Scope mode:

- **stash** — on the default branch, create a branch first (kebab-case, no
  `/`). Stage exactly `changed.paths` and commit with the title as the
  message, then push with upstream.
- **branch** — push the current branch.
- **sidecar** — push the current branch; the dirty sidecar paths stay
  uncommitted.
- **pinned** — reuse the preview worktree and branch. Confirm its tree is
  clean, `HEAD` equals `$SCRATCH/preview.head`, and
  `git -C "$PREVIEW_TREE" rev-list --count "$DEFAULT_REF"..HEAD` is exactly
  one, then push `$PREVIEW_BRANCH`. The user's worktree must still match the
  Scope snapshot.

**Create or update the PR.** `--attach` rewrites each local reference in
`body.md` in place and gives the video an inline player. Repeat `--attach`
once per file the body references; drop the mp4 on stills-only PRs. Expand
`$SCRATCH` to the same absolute path in the body and in `--attach`.

```bash
# no PR yet
gh pr create --title "<title>" --body-file "$SCRATCH/body.md" \
  --attach "$SCRATCH/pr-demo.mp4" \
  --attach "$SCRATCH/<slug>-before.png" \
  --attach "$SCRATCH/<slug>-after.png"

# PR exists — replace its title and description
gh pr edit --title "<title>" --body-file "$SCRATCH/body.md" \
  --attach "$SCRATCH/pr-demo.mp4" \
  --attach "$SCRATCH/<slug>-before.png" \
  --attach "$SCRATCH/<slug>-after.png"
```

An attachment command can partially succeed and still create or update the
PR. After every command, reopen the result with `gh pr view` or `gh api` and
require every local reference to have become a remote asset, with the images
and player present. A nonzero command with a created PR is a repairable
attachment failure: repair it with `gh pr edit` on that PR.

Pinned cleanup: after publication remove only `$PREVIEW_TREE` and keep the
pushed branch for the PR. When the user declines, remove `$PREVIEW_TREE`, then
delete `$PREVIEW_BRANCH`.
