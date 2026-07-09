# Docs (v1)

```bash
gws docs <resource> <method> [flags]
```

## Helper: +write

Append text to a document (inserted at the end of the document body).

```bash
gws docs +write --document <ID> --text <TEXT>
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--document` | Yes | — | Document ID |
| `--text` | Yes | — | Text to append (plain text) |

**Example:**

```bash
gws docs +write --document DOC_ID --text 'Hello, world!'
```

For rich formatting, use the raw `batchUpdate` API instead.

> Write command — confirm with the user before executing.

## API Resources

### documents

- `batchUpdate` — Apply one or more updates to a document. All-or-nothing — if any request is invalid, nothing is applied.
- `create` — Create a blank document with a title. Only `form.info.title` and `form.info.document_title` are used; other fields are ignored.
- `get` — Get the latest version of a document.
