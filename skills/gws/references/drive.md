# Drive (v3)

```bash
gws drive <resource> <method> [flags]
```

## Helper: +upload

Upload a file with automatic metadata (MIME type detected automatically).

```bash
gws drive +upload <file> [--parent FOLDER_ID] [--name 'Target Name']
```

**Examples:**

```bash
gws drive +upload ./report.pdf
gws drive +upload ./report.pdf --parent FOLDER_ID
gws drive +upload ./data.csv --name 'Sales Data.csv'
```

> Write command — confirm with the user before executing.

## API Resources

### about

- `get` — User info, Drive info, and system capabilities. The `fields` parameter is required.

### accessproposals

- `get` — Retrieve an access proposal by ID.
- `list` — List access proposals on a file (approvers only).
- `resolve` — Approve or deny an access proposal.

### apps

- `get` — Get a specific installed app.
- `list` — List a user's installed apps.

### changes

- `getStartPageToken` — Get the starting pageToken for listing future changes.
- `list` — List changes for a user or shared drive.
- `watch` — Subscribe to changes for a user.

### channels

- `stop` — Stop watching resources through a channel.

### comments

- `create` — Create a comment on a file. `fields` parameter required.
- `delete` — Delete a comment.
- `get` — Get a comment by ID. `fields` parameter required.
- `list` — List a file's comments. `fields` parameter required.
- `update` — Update a comment (patch semantics). `fields` parameter required.

### drives

- `create` — Create a shared drive.
- `get` — Get a shared drive's metadata by ID.
- `hide` — Hide a shared drive from the default view.
- `list` — List the user's shared drives. Supports `q` search parameter.
- `unhide` — Restore a shared drive to the default view.
- `update` — Update metadata for a shared drive.

### files

- `copy` — Copy a file with optional patch updates.
- `create` — Create a file (max 5,120 GB).
- `download` — Download file content (valid for 24 hours).
- `export` — Export a Google Workspace document to a requested MIME type (max 10 MB).
- `generateIds` — Generate file IDs for use in create or copy requests.
- `get` — Get a file's metadata or content by ID. Use `alt=media` param for content.
- `list` — List the user's files. Supports `q` search parameter. Returns trashed files by default; add `trashed=false` to exclude.
- `listLabels` — List labels on a file.
- `modifyLabels` — Modify labels on a file.
- `update` — Update a file's metadata and/or content (patch semantics, max 5,120 GB).
- `watch` — Subscribe to changes on a file.

### operations

- `get` — Get the state of a long-running operation.

### permissions

- `create` — Create a permission for a file or shared drive.
- `delete` — Delete a permission.
- `get` — Get a permission by ID.
- `list` — List a file's or shared drive's permissions.
- `update` — Update a permission (patch semantics).

> Concurrent permissions operations on the same file aren't supported — only the last update is applied.

### replies

- `create` — Create a reply to a comment.
- `delete` — Delete a reply.
- `get` — Get a reply by ID.
- `list` — List a comment's replies.
- `update` — Update a reply (patch semantics).

### revisions

- `delete` — Permanently delete a file version (binary content only — not Docs/Sheets/Slides).
- `get` — Get a revision's metadata or content by ID.
- `list` — List a file's revisions (may be incomplete for frequently edited files).
- `update` — Update a revision (patch semantics).
