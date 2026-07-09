# Slides (v1)

```bash
gws slides <resource> <method> [flags]
```

## API Resources

### presentations

- `batchUpdate` — Apply one or more updates to a presentation. All-or-nothing — if any request is invalid, nothing is applied.
- `create` — Create a blank presentation with a title. If a `presentationId` is provided, it's used as the ID; otherwise one is generated.
- `get` — Get the latest version of a presentation.
- `pages` — Operations on the pages resource.
