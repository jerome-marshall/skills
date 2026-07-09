# Tasks (v1)

```bash
gws tasks <resource> <method> [flags]
```

## API Resources

### tasklists

- `delete` — Delete a task list. If the list contains assigned tasks, both the assigned and original tasks are deleted.
- `get` — Get a specific task list.
- `insert` — Create a new task list (max 2,000 lists per user).
- `list` — List all task lists.
- `patch` — Update a task list (patch semantics).
- `update` — Update a task list.

### tasks

- `clear` — Clear all completed tasks from a list (marks them as hidden).
- `delete` — Delete a task. If assigned (from Docs/Chat), both instances are deleted.
- `get` — Get a specific task.
- `insert` — Create a new task (max 20,000 non-hidden per list, 100,000 total). Tasks assigned from Docs/Chat cannot be created via this API.
- `list` — List all tasks in a list (doesn't return assigned tasks by default).
- `move` — Move a task to another position, including under a new parent (max 2,000 subtasks per task).
- `patch` — Update a task (patch semantics).
- `update` — Update a task.
