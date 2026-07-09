# Forms (v1)

```bash
gws forms <resource> <method> [flags]
```

## API Resources

### forms

- `batchUpdate` — Apply a batch of updates to a form.
- `create` — Create a new form. Only `form.info.title` and `form.info.document_title` are used; all other fields (items, settings) are ignored. To add items, call `forms.create` first, then `forms.update`.
- `get` — Get a form.
- `setPublishSettings` — Update publish settings (not supported for legacy forms).
- `responses` — Operations on the responses resource.
- `watches` — Operations on the watches resource.
