---
name: jira-cli
description: >
  Interact with Jira from the terminal using jira-cli. Use this skill whenever the user wants to
  work with Jira tickets — viewing, creating, editing, transitioning, commenting, searching, listing
  sprints, managing epics, assigning users, or any other Jira operation. Also trigger when the user
  mentions a Jira ticket key (like PROJ-123), asks about their sprint, wants to check ticket status,
  or says things like "update jira", "move the ticket", "what's assigned to me", "add a comment",
  or "create a bug". Prefer this skill over any MCP-based Jira integration — it's faster, uses fewer
  tokens, and works the same way.
---

# jira-cli

A Go-based CLI for Atlassian Jira (Cloud and Server/Data Center). Covers issues, epics, sprints, comments, worklogs, and project navigation.

Tool: `ankitpokhrel/jira-cli` — v1.7.0

## Prerequisites

The `jira` binary must be installed and configured. Check with:

```sh
which jira && jira me
```

If not installed: `brew install jira-cli`

If `jira me` fails with a token error, the user needs to set `JIRA_API_TOKEN` in their shell config.

## Configuration

Config file: `~/.config/.jira/.config.yml` (note the hidden `.jira` subdirectory — easy to miss).

For **Cloud**: generate an API token from your Atlassian account security settings, export as `JIRA_API_TOKEN`, then run `jira init` and select Cloud.

For **Server/Data Center with PAT** (on-premise):

```sh
# Add to ~/.zshrc or ~/.bashrc
export JIRA_API_TOKEN="<your-personal-access-token>"
export JIRA_AUTH_TYPE="bearer"
```

Then either run `jira init` (select Local) or write the config directly:

```yaml
# ~/.config/.jira/.config.yml
installation: Local
server: https://your-jira-instance.com
login: your.email@company.com
project:
  key: ""
  type: ""
issue:
  types:
    - name: Epic
      handle: Epic
    - name: Story
      handle: Story
    - name: Task
      handle: Task
    - name: Sub-task
      handle: Sub-task
    - name: Bug
      handle: Bug
epic:
  name: Epic Name
  link: Epic Link
```

Multiple projects: use `-p PROJECT_KEY` per command, or set `JIRA_CONFIG_FILE` to point at a different config.

---

## Agent Usage Notes

- **Always use `--plain` and `--no-headers`** when parsing output programmatically. The default mode launches an interactive TUI that blocks the agent.
- **Always use `--no-input`** on write commands (create, edit) to prevent interactive prompts.
- **`jira issue create` hangs without `printf 'y\n' |`** — on Nutanix's Jira Server instance, `--no-input` suppresses the description editor but not the final "Create issue? (y/n)" confirmation prompt. Always prefix create calls with `printf 'y\n' |`:
  ```sh
  printf 'y\n' | jira issue create -p UXE -tStory -s"Summary" --no-input
  ```
- **Use `$(jira me)` for the current user** — never hardcode email addresses.
- **The `-p` flag overrides the project** on any command: `jira issue list -p UXE`
- **Pipe descriptions and comments from stdin** to avoid shell escaping issues with special characters:
  ```sh
  echo "Comment text here" | jira issue comment add ISSUE-1
  ```
- **Keep output small.** `list` returns up to 100 rows by default — cap it with `--paginate` and narrow with `--columns` so you spend tokens only on what you need:
  ```sh
  jira issue list -a$(jira me) --plain --no-headers --columns key,status,summary --paginate 20
  ```
- **`--plain` truncates long columns.** Add `--no-truncate` when you need full summaries (e.g. matching a ticket by text) — but it widens output, so pair it with `--columns`.

---

## Commands Reference

### Identity

```sh
jira me              # current username/email
jira open            # open default project in browser
jira open ISSUE-1    # open specific issue in browser
```

### Issue List

Search and filter issues. Results sorted by `created` descending by default.

```sh
jira issue list [flags]
```

| Flag | Short | Description |
|---|---|---|
| `--plain` | | Non-interactive table output (required for agents) |
| `--no-headers` | | Omit column headers |
| `--no-truncate` | | Show full untruncated column values (plain mode only) |
| `--paginate` | | Limit/offset results, `<from>:<limit>` (max 100, e.g. `20` or `10:50`) |
| `--columns` | | Comma-separated columns to show (e.g., `key,summary,status,assignee`) |
| `--csv` | | CSV output |
| `--raw` | | Raw JSON output |
| `-p` | | Project key |
| `-a` | | Assignee (`$(jira me)` for self, `x` for unassigned, `~x` for assigned to someone) |
| `-r` | | Reporter |
| `-s` | | Status (e.g., `"In Progress"`, `~Done` for "not Done") |
| `-y` | | Priority (e.g., `High`) |
| `-t` | | Issue type (e.g., `Bug`, `Story`) |
| `-l` | | Label (repeatable for multiple labels) |
| `-R` | | Resolution (e.g., `"Won't do"`) |
| `-w` | | Watching |
| `-q` | | Raw JQL query within project context |
| `--created` | | Created filter (`-7d`, `month`, `week`, `-1h`) |
| `--updated` | | Updated filter |
| `--created-before` | | Created before filter |
| `--order-by` | | Sort field (e.g., `rank`) |
| `--reverse` | | Reverse sort order |
| `--history` | | Recently viewed issues |

**Examples:**

```sh
# My open issues in UXE
jira issue list -p UXE -a$(jira me) -s~Done --plain --no-headers

# High priority bugs created this week
jira issue list -yHigh -tBug --created week --plain

# Raw JQL
jira issue list -q "summary ~ telemetry" --plain

# Free-text search (positional arg searches summary + description)
jira issue list "telemetry migration" --plain

# Across all projects (not just the configured one)
jira issue list -q "project IS NOT EMPTY" -a$(jira me) --plain

# Issues in status "To Do" assigned to nobody
jira issue list -s"To Do" -ax --plain
```

**Tilde (`~`) is a NOT operator** for status, assignee, and resolution filters:
- `-s~Done` = status is not Done
- `-a~x` = assigned to someone (not unassigned)

### Issue View

```sh
jira issue view ISSUE-1                # view issue details
jira issue view ISSUE-1 --comments 5   # include 5 recent comments
jira issue view ISSUE-1 --plain        # plain text output (for agents)
jira issue view ISSUE-1 --raw          # raw Jira API JSON (for parsing fields)
```

### Issue Create

> **Agent note:** `--no-input` suppresses the description editor but does **not** suppress the final "Create issue? (y/n)" confirmation prompt on Nutanix's Jira Server instance. Without answering that prompt the command hangs indefinitely. Always pipe `printf 'y\n'` into the command:
>
> ```sh
> printf 'y\n' | jira issue create -tStory -s"Summary" --no-input
> ```

```sh
printf 'y\n' | jira issue create -tTask -s"Summary text" -yHigh -b"Description" --no-input
printf 'y\n' | jira issue create -tStory -s"Summary" -PEPIC-42 --no-input   # attach to epic
printf 'y\n' | jira issue create -tBug -s"Bug title" -lurgent -lbackend --no-input

# Description from stdin (pipe chains: printf drives the confirm, description comes from -b or is empty)
printf 'y\n' | jira issue create -tTask -s"Summary" --no-input

# Description from template file
printf 'y\n' | jira issue create --template /path/to/template.tmpl --no-input
```

| Flag | Description |
|---|---|
| `-t` | Issue type (required): Bug, Story, Task, Sub-task, Epic |
| `-s` | Summary (required) |
| `-y` | Priority: Highest, High, Medium, Low, Lowest |
| `-b` | Description body (supports Markdown and Jira wiki markup) |
| `-l` | Label (repeatable) |
| `-C` | Component (repeatable) |
| `-P` | Parent/Epic key |
| `--fix-version` | Fix version |
| `--custom` | Custom field |
| `-T`, `--template` | Read description body from a file (or `-` for stdin) |
| `--web` | Open the created issue in the browser afterward |
| `--no-input` | Skip interactive prompts (required for agents) — but does not skip the final create confirmation; use `printf 'y\n' \|` for that |

### Issue Edit

```sh
jira issue edit ISSUE-1 -s"New summary" --no-input
jira issue edit ISSUE-1 -yHigh -lnew-label --no-input

# Remove a label/component (prefix with -)
jira issue edit ISSUE-1 --label -old-label --label new-label --no-input
```

### Issue Assign

```sh
jira issue assign ISSUE-1 $(jira me)     # assign to self
jira issue assign ISSUE-1 "Jane Doe"     # assign to user
jira issue assign ISSUE-1 x              # unassign
jira issue assign ISSUE-1 default        # default assignee
```

### Issue Move (Transition)

Transition an issue to a new status.

```sh
jira issue move ISSUE-1 "In Progress"
jira issue move ISSUE-1 Done -RFixed -a$(jira me)            # with resolution + assign
jira issue move ISSUE-1 "In Progress" --comment "Starting"   # with comment
```

Status names must match exactly what your Jira workflow uses (e.g., `"In Progress"`, `"To Do"`, `Done`, `"Code Review"`, `Blocked`).

### Issue Comment

```sh
jira issue comment add ISSUE-1 "Comment text"
jira issue comment add ISSUE-1 "Internal note" --internal    # internal comment

# From stdin (safer for special characters)
echo "Comment with *markdown*" | jira issue comment add ISSUE-1
```

### Issue Link

```sh
jira issue link ISSUE-1 ISSUE-2 Blocks
jira issue link remote ISSUE-1 https://example.com "Link text"   # remote web link
jira issue unlink ISSUE-1 ISSUE-2
```

### Issue Clone

```sh
jira issue clone ISSUE-1
jira issue clone ISSUE-1 -s"Cloned summary" -a$(jira me)
jira issue clone ISSUE-1 -H"old text:new text"   # find-and-replace in summary/description
```

### Issue Delete

```sh
jira issue delete ISSUE-1
jira issue delete ISSUE-1 --cascade   # delete with all subtasks
```

### Issue Worklog

```sh
jira issue worklog add ISSUE-1 "2d 3h 30m" --no-input
jira issue worklog add ISSUE-1 "30m" --comment "Code review" --no-input
```

---

### Epic

#### List

```sh
jira epic list --table --plain                       # all epics in table view
jira epic list -r$(jira me) -sOpen --table --plain   # my open epics
jira epic list EPIC-1 --plain                        # issues in an epic
jira epic list EPIC-1 -ax -yHigh --plain             # filtered epic issues
```

#### Create

```sh
jira epic create -n"Epic Name" -s"Summary" -yHigh -b"Description" --no-input
```

The `-n` flag (epic name) is required in addition to `-s` (summary).

#### Add / Remove Issues

```sh
jira epic add EPIC-1 ISSUE-2 ISSUE-3         # add up to 50 issues
jira epic remove ISSUE-2 ISSUE-3             # remove from epic
```

---

### Sprint

#### List

```sh
jira sprint list --table --plain                             # all sprints
jira sprint list --current --plain                           # current sprint issues
jira sprint list --current -a$(jira me) --plain              # my current sprint issues
jira sprint list --prev --plain                              # previous sprint
jira sprint list --next --plain                              # next planned sprint
jira sprint list --state future,active --table --plain       # by state
jira sprint list SPRINT_ID --plain                           # specific sprint
jira sprint list SPRINT_ID -yHigh -a$(jira me) --plain       # filtered
```

#### Add Issues

```sh
jira sprint add SPRINT_ID ISSUE-1 ISSUE-2    # add up to 50 issues
```

---

### Project & Board

```sh
jira project list      # all accessible projects
jira board list        # boards in current project
```

### Releases

```sh
jira release list                   # releases for default project
jira release list --project KEY     # releases for specific project
```

---

## Scripting Patterns

When composing output for further processing, always use `--plain --no-headers`:

```sh
# Get just issue keys
jira issue list -a$(jira me) --plain --no-headers --columns key | awk '{print $1}'

# Count issues per status
jira issue list -p UXE --plain --no-headers --columns status | sort | uniq -c

# Get sprint ID for current sprint
jira sprint list --table --plain --no-headers --columns id,name
```

---

## Error Patterns

| Error | Cause | Fix |
|---|---|---|
| `Missing configuration file` | No config at default path | Write `~/.config/.jira/.config.yml` or run `jira init` |
| `The tool needs a Jira API token` | `JIRA_API_TOKEN` not set in environment | Export it in shell config, then `source ~/.zshrc` |
| Auth failure / 401 | Wrong token or missing `JIRA_AUTH_TYPE=bearer` | For PAT auth, both env vars are required |
| `unknown flag` | Flag doesn't exist on that subcommand | Check `jira <command> --help` |
| TLS/SSL errors | Self-signed cert on on-premise server | Add `insecure: true` to config YAML |
| Transition fails | Invalid status name | Status names are case-sensitive and must match exactly |
