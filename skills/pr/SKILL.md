---
name: pr
description: "Opens or updates a GitHub pull request as a draft, with a body that's fast to review and proof that the change works. Use whenever opening or updating a PR, deciding whether work should be one PR, separate PRs or a stack, or handing PR work to parallel agents. GitHub only, through `gh`."
---

Turn committed work into a **draft** PR a reviewer trusts in under a minute: what changed, proof it works, and how risky it is to merge. The draft is the gate: the human marks it ready, so you open it and stop.

The skill starts once the code is committed and ends at a published draft. Scratch lives outside the repo: `SCRATCH="${TMPDIR:-/tmp}/pr-<branch>"`. Screenshots and logs stay there, off the branch, and are kept after upload so revisions can reuse them.

## Steps

1. **Shape.** Decide how many PRs this work becomes and each one's base, per [Shape](#shape). Done when every change belongs to exactly one PR and each PR has a base.
2. **Claims.** Read the diff GitHub will show (`git diff origin/<base>...HEAD`) and write each change as a **claim**: one sentence a reviewer could check by looking or running. Done when every changed file sits under a claim or is named in the Scope line.
3. **Proof.** Prove each claim with the lowest rung of the [proof ladder](#proof-ladder) that carries it. Done when every claim has its proof or a "Not verified: <why>" line.
4. **Body.** Write `$SCRATCH/body.md` and a title, per [Body](#body). Done when every claim appears in Evidence and every referenced file exists.
5. **Publish.** Push and open or update the draft, per [Publish](#publish). Done when the read-back passes.
6. **Report.** Post the PR URL, one line on what was proved and one on what wasn't, then stop. A helper under an orchestrator reports per [delegate](references/delegate.md#report).

## Shape

Ask of each change: **would this build, pass CI and make sense if it were the only thing merged into main?**

- Yes, and it's one change: one PR on the default branch.
- Yes, and there are several unrelated changes: one PR each, every one on the default branch, each in its own worktree, even when built in parallel.
- No, it needs another open PR's code: a stack, one concern per layer, foundation at the bottom, built with the `gh-stack` skill.
- Unrelated fixes that touch the same lines: one combined PR, or a stack whose body says the dependency is textual.

Why chaining unrelated fixes hurts, and stack layers in worktrees: [stacks](references/stacks.md). Handing PRs to parallel helpers: [delegate](references/delegate.md). Branch names follow the repo's and the user's conventions.

**Base** is the PR's real base: `gh pr view --json baseRefName`; with no PR yet, the nearest unmerged branch below in the stack, else the default branch. An orchestrator's handoff names it. **Before** is `git merge-base HEAD origin/<base>` after fetching the base, the same three-dot diff GitHub shows reviewers.

## Proof ladder

Each row adds to the rows above only when the change really is that kind.

| Change | Minimum proof |
| --- | --- |
| No runtime change (docs, comments, rename) | One line saying why. CI green. |
| Refactor that keeps behavior | The covering tests by name, plus "no test files changed" or the list of test edits. |
| Visual tweak | One before/after screenshot pair, with route and action. After-only for brand-new UI. A second viewport only if responsive rules changed. |
| Bug fix or logic change | A test that goes **red** with the fix reverted and **green** with it. Revert only the source files and keep the new test. No test harness: real command output before and after. |
| Feature without UI interaction | New tests plus one real run (curl, CLI) with its output. |
| Interaction, motion, multi-step flow | Stills of the key states plus one short video, made with the `record-ui-walkthrough` skill, only because a still can't show it. |
| Sensitive area (auth, secrets, CI, weakened tests) | The above, plus a note on what could go wrong and what was checked. |
| One-way door (migration, data, public contract) | Migrate and rollback output, affected rows, a recovery plan, and the Hard to undo line in [Body](#body). |

At every rung: proof comes from the head being merged, so rerun it after a rebase. Name what you didn't verify ("Not verified: Safari"). List every deleted, skipped or weakened test.

**Running the app** is the repo's business. Use what it documents (a verify skill, `AGENTS.md`, README, its scripts); with nothing documented, work it out and say in Evidence how you ran it. **Ready** means you can observe the change: the changed element on the page, the new behavior from the service or CLI. A startup log line or an HTTP 200 is not ready. Keep long-running processes alive with your harness's background mode or tmux, and stop only what you started.

**Capturing before.** Keep the app running. Revert the changed source files in place, let the app reload, capture, then restore and check `git status` matches where you started:

```bash
git restore --source="$(git merge-base HEAD origin/<base>)" --worktree -- <source files>
git restore --source=HEAD --worktree -- <source files>
```

Use a separate worktree of the base only when the in-place revert can't work (no reload, generated code, schema changes).

**Screenshots.** Use `agent-browser` if it's installed, otherwise whatever browser automation is available, at the viewport the claim needs.

- Always a full-viewport before/after pair, scrolled so the change and its surroundings are in view. Add a zoomed pair of the changed area when the change is small relative to the page; capture the full page only when its shape changed.
- Leave subtle changes (gap, alignment, color) unpainted. For a discrete element, draw a thin outline set slightly off it, on the shot where the element exists. Skip arrows and text callouts.
- Use demo or test data. Open every image before upload and retake any that shows secrets or personal data.

## Body

**Template first.** If the repo has a PR template (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/` or the root), fill it. Its required fields (ticket, change type, checklists) stay at the top word for word. Add a section below only where the template has nothing similar. With no template:

```markdown
## Summary
<What changed and why, 1–3 sentences. Ticket link.>
**Scope:** <what this covers; what it deliberately leaves out>

## Evidence
- **<claim>**: <live UI | test red→green | command output | not verified: why>

## Blast Radius
**Door:** <two-way: a revert undoes it | one-way: why>
**Reaches:** <what could break, and who consumes it>
**Look at:** <one or two places to read first>
**Tests/CI changed:** <none | list>
**Not verified:** <none | list>
```

Write a briefing, about 40 lines at most. A rejected alternative a reviewer would ask about gets one sentence in Summary. An optional visual (diff sketch, call tree, diagram) goes in Summary, per [summary](references/summary.md). In Evidence, lead each screenshot pair with its claim, route and action, then a two-column Before | After table. A video sits in its own paragraph (`![](/abs/scratch/walkthrough.mp4)`) so GitHub renders a player. A red/green test shows the command, then what failed before and passes now.

These lines go at the very top of the body when they apply:

- A hard-to-undo change: "Hard to undo: <why>. Needs an owner's review before ready."
- The app couldn't run: "Not verified: live UI, <reason>." Open the draft anyway with the strongest proof you have.
- A judgment call you couldn't settle: one short question for the reviewer.

**Updating a PR.** Keep text a human wrote and work it in; replace only placeholders and what an agent wrote. After new commits, rewrite the body to describe the current head and rerun proof only for the claims those commits touch.

**Title** follows the repo's convention, read from recent merged titles (`gh pr list --state merged --limit 15 --json title`). Include a ticket key only when the branch or commits name one and the convention uses keys.

## Publish

```bash
git push -u origin HEAD
gh pr create --draft --base <base> --title "<title>" --body-file "$SCRATCH/body.md" \
  --attach "$SCRATCH/<slug>-before.png" --attach "$SCRATCH/<slug>-after.png"
gh pr edit <number> --title "<title>" --body-file "$SCRATCH/body.md" --attach ...   # existing PR
gh pr view <number> --json isDraft,body
```

`--attach` uploads each file and rewrites the matching local path in the body; pass one per file, with the same absolute path the body uses. A partial upload failure still creates or updates the PR and exits nonzero, so repair it with `gh pr edit`. The read-back passes when a new PR is a draft and the body has no local paths left (`/tmp/`, `/var/folders/`, `/Users/`, `/home/`).

An existing PR keeps whatever draft or ready state it has. Marking ready, CI and review comments belong to the human or a separate step, so the run ends here.
