# Sheets (v4)

```bash
gws sheets <resource> <method> [flags]
```

## Helper: +read

Read values from a spreadsheet (read-only, never modifies). Supports tab selection via the range parameter.

```bash
gws sheets +read --spreadsheet <ID> --range <RANGE>
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--spreadsheet` | Yes | — | Spreadsheet ID |
| `--range` | Yes | — | Range to read (e.g. `"My Tab!A1:B2"` or just `"My Tab"` for entire tab) |

**Examples:**

```bash
gws sheets +read --spreadsheet ID --range "Sheet1!A1:D10"
gws sheets +read --spreadsheet ID --range "My Tab Name"
```

## Helper: +append

Append rows to a spreadsheet. **Limitation: always appends to the first tab (ignores `--range` for tab selection).** If you need to target a specific tab, use the raw API (see "Append to a specific tab" below).

```bash
gws sheets +append --spreadsheet <ID> --values <CSV>
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--spreadsheet` | Yes | — | Spreadsheet ID |
| `--values` | — | — | Comma-separated values (simple single row) |
| `--json-values` | — | — | JSON array of rows, e.g. `'[["a","b"],["c","d"]]'` |

Only use `+append` when targeting the default (first) tab:

```bash
gws sheets +append --spreadsheet ID --values 'Alice,100,true'
gws sheets +append --spreadsheet ID --json-values '[["a","b"],["c","d"]]'
```

> Write command — confirm with the user before executing.

---

## Recipes

Common multi-step operations. Use these instead of figuring out the raw API from scratch.

### Append to a specific tab

The `+append` helper doesn't support tab selection, so use the raw `values append` API. Pass the tab name in the `range` field inside `--params`:

```bash
gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"SPREADSHEET_ID","range":"Tab Name!A1","valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"}' \
  --json '{"values":[["col1","col2","col3"]]}'
```

- `range` — use `"Tab Name!A1"` (the `!A1` tells the API where to start looking for the table)
- `valueInputOption` — `RAW` (store literally) or `USER_ENTERED` (parse formulas/dates)
- `insertDataOption` — `INSERT_ROWS` (adds new rows) or `OVERWRITE` (overwrites existing)

Multiple rows:

```bash
--json '{"values":[["row1col1","row1col2"],["row2col1","row2col2"]]}'
```

### Delete a row

Deleting a row requires two pieces of info that aren't obvious:
1. The tab's internal **sheet ID** (a number, different from the spreadsheet ID)
2. The row's **0-based index** (row 1 in the sheet = index 0)

**Step 1 — Get the tab's sheet ID:**

```bash
gws sheets spreadsheets get \
  --params '{"spreadsheetId":"SPREADSHEET_ID","fields":"sheets.properties"}'
```

This returns all tabs with their `sheetId` and `title`. Find the one you need.

**Step 2 — Delete the row:**

```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId":"SPREADSHEET_ID"}' \
  --json '{"requests":[{"deleteDimension":{"range":{"sheetId":SHEET_ID,"dimension":"ROWS","startIndex":ROW_INDEX,"endIndex":ROW_INDEX_PLUS_1}}}]}'
```

- `startIndex` is inclusive, `endIndex` is exclusive (both 0-based)
- To delete row 4 as seen in the sheet: `startIndex: 3, endIndex: 4`
- To delete multiple consecutive rows (e.g. rows 4–6): `startIndex: 3, endIndex: 6`

**Full example — delete row 4 from a tab called "My Tab" with sheet ID 1864427570:**

```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId":"abc123"}' \
  --json '{"requests":[{"deleteDimension":{"range":{"sheetId":1864427570,"dimension":"ROWS","startIndex":3,"endIndex":4}}}]}'
```

### Clear cell values (without deleting rows)

Use `values clear` to empty cell contents while keeping the rows/structure intact:

```bash
gws sheets spreadsheets values clear \
  --params '{"spreadsheetId":"SPREADSHEET_ID","range":"Tab Name!A4:G4"}'
```

### Update specific cells

Overwrite values in a specific range:

```bash
gws sheets spreadsheets values update \
  --params '{"spreadsheetId":"SPREADSHEET_ID","range":"Tab Name!A2:C2","valueInputOption":"RAW"}' \
  --json '{"values":[["new1","new2","new3"]]}'
```

### Read all tab names and sheet IDs

Useful before any operation that needs a sheet ID (deletions, moves, formatting):

```bash
gws sheets spreadsheets get \
  --params '{"spreadsheetId":"SPREADSHEET_ID","fields":"sheets.properties"}'
```

Returns JSON with each tab's `sheetId`, `title`, `index`, and grid dimensions.

---

## Raw API Resources

For operations not covered by recipes above, use the full API path:

```bash
gws sheets spreadsheets <resource> <method> --params '...' --json '...'
```

### spreadsheets

- `batchUpdate` — Apply one or more updates (formatting, delete rows/columns, merge cells, etc.). All-or-nothing.
- `create` — Create a new spreadsheet.
- `get` — Get spreadsheet metadata. Grid data not returned by default; use `fields` or set `includeGridData=true`.
- `getByDataFilter` — Get a spreadsheet with data filters for selective data return.

### spreadsheets.values

- `append` — Append rows to a table found within a range.
- `batchClear` — Clear multiple ranges at once.
- `batchGet` — Read multiple ranges in one call.
- `batchUpdate` — Write to multiple ranges in one call.
- `clear` — Clear a single range.
- `get` — Read a single range.
- `update` — Overwrite a single range.

### spreadsheets.sheets

- Operations on individual sheets (tabs) within a spreadsheet.

### spreadsheets.developerMetadata

- Operations on developer metadata attached to sheets.
