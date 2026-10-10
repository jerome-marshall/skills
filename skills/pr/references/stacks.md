# Stacks

When work becomes more than one PR. The decision rule lives in [SKILL.md](../SKILL.md#shape); this file is the why and the edge cases. Commands for creating, syncing and merging stacks live in the `gh-stack` skill.

A stack has one job: shipping **dependent** work in reviewable layers, where each layer **builds on** the one below. Independent work, even many fixes from one ticket or one session, ships as **siblings**: separate PRs, each on the default branch.

## Why chaining unrelated fixes hurts

A chain of independent fixes looks tidy and costs a lot:

- **Merges queue.** A PR can't merge until every PR below it is approved and green. One slow review blocks every fix above it.
- **Dropping one is disruptive.** Closing a middle PR blocks everything above it until the stack is unstacked and rebuilt.
- **Every fix churns the rest.** A review change low in the chain forces a rebase and force-push of every layer above, and a CI rerun on each.
- **Proof goes wrong.** A mid-chain PR's base already contains the fixes below it, so its "before" shows a state that never existed on main.

Siblings avoid all four: each merges on its own schedule, and each "before" is main.

"One issue per PR, the first on main, each next on the previous" is right only for dependent work. For independent issues, keep one issue per PR and point every PR at main.

## Fixes that touch the same lines

Two "unrelated" fixes that edit the same lines aren't independent in git, even if they are in meaning: as siblings, the second to merge conflicts. Either:

- combine them into one PR, with one claim each in Evidence; or
- stack them, and say in the upper PR's Summary that the dependency is textual ("Stacked on #12 only because both edit `Header.tsx` lines 40–60").

Pick combining when the fixes are small and reviewed by the same people; pick a stack when each needs its own review.

## Stack context

Each PR in a stack gets one line under Summary: the stack's goal and this layer's place in it.

```markdown
**Stack:** 2 of 3 toward <goal>. Builds on #41 (<what that layer adds>).
```

## Choosing the base

Resolve the base in this order; an orchestrator's handoff overrides all of it.

1. The PR exists: `gh pr view --json baseRefName --jq .baseRefName`.
2. No PR yet, and `gh stack view --json` lists the current branch: the nearest **unmerged** branch listed before it (branches run bottom to top), else `trunk`. Each entry's `base` field is a SHA, not a branch name, so read the name from the list.
3. Otherwise the default branch: `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`.

Then fetch it and take the merge-base, which is what GitHub diffs:

```bash
git fetch origin "+refs/heads/<base>:refs/remotes/origin/<base>"
git merge-base HEAD "origin/<base>"
```

If the parent branch isn't pushed yet, use the local branch. When `gh stack view --json` shows `needsRebase`, restack first: the merge-base and the parent's tip disagree until you do.

When a lower PR merges, GitHub retargets the next one, and its diff stays the same relative to its parent. Existing proof stays valid unless the parent's content under a claim changed.

## Stack layers in worktrees

Parallel work and stacks mix only along the dependency line:

- **Siblings** run fully in parallel, each in a worktree created from the default branch.
- **Layers** run one after another. Create each layer's worktree from its parent's branch, after the parent has committed:

```bash
git worktree add -b <child-branch> <path> <parent-branch>
```

Some built-in worktree features (Claude Code's, for one) always branch from the default branch. They're right for siblings and wrong for layers; create layer worktrees with `git` directly.

Keep the worktrees on one stack quiet while history is rewritten: a restack or sync touches every layer, so pause helpers working on those layers until it finishes.
