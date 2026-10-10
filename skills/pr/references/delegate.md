# Delegating PRs to helpers

For an orchestrator that hands tasks to helper agents, each of which opens its own draft PR. The human samples the drafts afterwards. The helper follows [SKILL.md](../SKILL.md); this file covers what the orchestrator does around it.

## Topology

Sort the tasks before spawning anything, with the [Shape](../SKILL.md#shape) question:

- **Independent tasks** run fully in parallel. Each gets a worktree from the default branch and a draft PR on the default branch.
- **Dependent layers** run one after another. A layer starts once its parent has committed, in a worktree created from the parent's branch ([stacks](stacks.md#stack-layers-in-worktrees)).
- A mix is several independent stacks and siblings, each sorted the same way.

Done when every task has a branch, a base, and a place in the order.

## Worktrees

One worktree per helper, created by the orchestrator so it knows each path and base:

```bash
git worktree add -b <branch> <path> origin/<default-branch>   # sibling
git worktree add -b <branch> <path> <parent-branch>          # stack layer
```

Branch names follow the repo's and the user's conventions. Each helper also gets its own scratch dir outside the repo, and its own port when the app runs once per worktree.

## Handoff

Pass **facts**. The skill is the recipe, so the message carries only what the helper can't find out itself:

```text
Read and follow the `pr` skill (~/.agents/skills/pr/SKILL.md). Where this message conflicts with it, the skill wins and you report the conflict.

Task: <ticket link, or the task in a short paragraph; say if you also write and commit the code>
Worktree: <absolute path>
Branch: <name>
Base: <branch>
PR: <number, or "none yet">
Scratch: <absolute path outside the repo>
Port: <reserved port, or "pick a free one">
Observations (from the user, unverified): <anything they said, or "none">

Open or update the draft only; leave its ready state alone. Write your report to <scratch>/report.md and reply with its path, a one-line status, the PR URL and the head SHA.
```

The helper decides the claims, the routes, where "before" comes from, the body, the risk wording and the title. Those come from reading the diff and running the change, which is the helper's work.

## Concurrency

Keep the number of helpers small, about three to five: heavy builds running at once slow each other down. Each helper keeps one running app for its whole run and captures "before" by reverting files in place, so it pays the startup cost once. When the app can only run once on the machine (a fixed port for OAuth, one local database), run the helpers' proof steps one at a time.

## Report

The helper writes `<scratch>/report.md` with these lines, in this order:

```markdown
status: done | partial | blocked: <why>
pr: <url>
head: <sha>
base: <branch>
claims:
- <claim>: live UI | test red→green | command output | not verified: <why>
ran app with: <command or documented route, one line>
conflicts: <none | where the handoff disagreed with the skill>
```

It replies with the report's path, the status line, the PR URL and the head SHA.

## Read-back

The orchestrator checks each PR itself instead of trusting the helper's reply:

```bash
gh pr view <url> --json isDraft,headRefOid,baseRefName,body
```

It passes when the PR is a draft, `headRefOid` matches the reported head, `baseRefName` matches the handoff, every claim in the report appears in Evidence, and the body has no local paths. A failed read-back goes back to that helper with the specific mismatch. Report to the human one line per PR: the URL, the status, and anything not verified.
