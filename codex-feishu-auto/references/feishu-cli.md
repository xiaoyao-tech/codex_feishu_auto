# Feishu CLI Playbook

Use this whenever the automation reads or writes a Feishu document through `lark-cli`.

## Identity

| Identity | Use when |
|---|---|
| `--as user` | The user owns the material wiki or the action must use user permissions. |
| `--as bot` | A bot owns or has explicit access to a shared automation document. |

Test with a read before writing. Bot and user permissions are separate. Do not run user login merely because a working bot path exists.

## Fetch before writing

```bash
lark-cli docs +fetch \
  --api-version v2 \
  --as user \
  --doc "$FEISHU_DOC" \
  --detail full \
  --format json
```

Use `--detail full` before edits so the response includes current revision, block IDs, styles, and references.

## Append a timeline card

```bash
LARK_CLI_NO_PROXY=1 lark-cli docs +update \
  --api-version v2 \
  --as user \
  --doc "$FEISHU_DOC" \
  --command append \
  --content '<h3>01:28 Update</h3><p>New fact...</p>'
```

Use append for chronological live notes. Do not append repeated heartbeats to the material document unless the user wants a complete run log.

## Insert near a heading

Fetch the document immediately before this action and use a fresh block ID:

```bash
lark-cli docs +update \
  --api-version v2 \
  --as user \
  --doc "$FEISHU_DOC" \
  --command block_insert_after \
  --block-id "$FRESH_HEADING_ID" \
  --content '<callout emoji="bulb"><p>Latest judgment...</p></callout>'
```

Cached block IDs can become invalid after human edits or prior replacements.

## Replace a structured table

For a maintained table, generate the complete XML table and replace the table block:

```bash
lark-cli docs +update \
  --api-version v2 \
  --as bot \
  --doc "$FEISHU_DOC" \
  --command block_replace \
  --block-id "$FRESH_TABLE_ID" \
  --content '<table>...</table>'
```

Do not use Markdown string replacement to insert rows into a native Feishu table. It can degrade the table into paragraphs.

## Insert an image

`lark-cli` file parameters accept paths relative to the current directory. Change into the image directory first:

```bash
cd "$WATCH_DIR/captures/selected"
lark-cli docs +media-insert \
  --api-version v2 \
  --as user \
  --doc "$FEISHU_DOC" \
  --file ./selected_frame.png \
  --align center \
  --caption "Official demo: ..."
```

An absolute path may be rejected as unsafe.

## Read back

After every write, fetch again and verify:

- revision advanced when a write occurred;
- content landed in the intended section;
- image and caption are visible;
- table remains a table;
- source links remain intact;
- timeline order is correct.

CLI success means the request returned successfully. It does not prove the editorial or operational result is correct.

## Human edits win

The live Feishu document is the collaboration surface. If a human deletes, moves, or rewrites content, treat that as intent. Never restore an old section from state or chat history unless the user explicitly asks.

## Errors

- Proxy EOF: retry once with `LARK_CLI_NO_PROXY=1`.
- Permission error: report current identity and missing scope; do not swap identities blindly.
- Stale block ID: fetch again and rebuild the precise update.
- Confirmation-required high-risk write: show the action and wait for explicit approval before retrying with confirmation.
- Partial write or wrong placement: do not overwrite the whole document as a shortcut. Fetch, locate, and repair the smallest block.
