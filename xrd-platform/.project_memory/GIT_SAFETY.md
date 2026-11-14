# Git and Working-Tree Safety

The human repository owner exclusively manages Git state and repository history.

## Forbidden for all agents

Do not execute:

- `git add`
- `git restore`
- `git checkout`
- `git switch`
- `git reset`
- `git clean`
- `git stash`
- `git commit`
- `git commit --amend`
- `git merge`
- `git rebase`
- `git cherry-pick`
- `git revert`
- `git push`
- `git pull`
- `git fetch`
- `git tag`
- `git worktree add`
- `git worktree remove`
- PR creation, update, merge, or branch-management commands

Do not stage files even temporarily.

## Allowed read-only inspection

Examples:

- `git status --short`
- `git diff`
- `git diff --stat`
- `git log`
- `git show`
- `git branch --show-current`
- `git worktree list`

## Working-tree ownership

Never assume an existing modification is disposable.

If a test/tool changes unrelated files unexpectedly:

1. stop;
2. do not restore or clean anything;
3. report exact affected files;
4. leave recovery to the human owner.

## Mutating tools

Independent reviewers must not run auto-fixing tools against the owner's primary working tree.

If actual execution of a mutating validator is required, use a disposable non-Git copy outside the repository, or report that safe in-place verification is impossible.
