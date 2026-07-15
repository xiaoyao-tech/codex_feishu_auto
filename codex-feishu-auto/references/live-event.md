# Live Event Workflow

Use this for model launches, keynotes, earnings calls, policy briefings, and other time-bounded live events.

## Before scheduling

1. Confirm the event timezone and convert key moments to the user's timezone.
2. Confirm the official live URL, official blog/release page, official social accounts, and at least one reputable liveblog.
3. Fetch the target Feishu document and verify the selected `--as user` or `--as bot` identity can read it.
4. Run one manual patrol before creating the automation.
5. Decide which facts deserve a strong alert.
6. Define event end, no-update threshold, and closeout output.

## Source hierarchy

Use this default order:

1. Official stream transcript or captions.
2. Official release page, documentation, system card, pricing, or API reference.
3. Official social accounts and GitHub releases.
4. Reputable liveblogs and news reports.
5. Community discussions and aggregators as leads only.

Do not flatten these into the same confidence level. If a media claim has no official support, preserve the attribution and verification gap.

## Per-round card

For every meaningful update, capture:

```markdown
### HH:MM Update | [short title]
- Source level: official / media / community / unverified
- Fact: what changed
- Main feature or scene: what the company is demonstrating
- Why it matters now: one editorial or product judgment
- Usable direction: headline or operational implication
- Evidence gap: what to verify next
```

This structure turns the live document into an editor's workbench rather than a link dump.

## Backtracking

Polling can land between two parts of the same announcement. During the live phase, re-read the latest 10-15 minutes of transcript and liveblog updates. Mark a recovered item as backfilled so the timeline remains understandable.

## Screenshots

Use screenshots for:

- model/product name slides;
- pricing and quota tables;
- benchmark or architecture slides;
- a product interaction that cannot be explained by text alone;
- a frame that proves the article's core claim.

Skip transitions, applause, repeated frames, decorative stage shots, and illegible tables.

Keep separate counts for:

- raw frames;
- reviewed or candidate frames;
- selected frames;
- frames actually inserted in Feishu.

The bundled capture script removes only exact duplicate files. Codex must still judge near-duplicates and informational value.

## Feishu layout

A practical live document has three zones:

1. Top callout: latest high-confidence judgment and immediate decisions.
2. Timeline: verified update cards in chronological order.
3. Material pool: selected screenshots and source links.

Use append for the timeline. Use a freshly fetched heading block ID for the top callout. Keep raw screenshots local; upload only selected evidence.

## Closeout

When the event ends and the no-update threshold is reached, produce:

- top 3 confirmed facts;
- strongest article or product angle;
- alternative angles;
- official evidence still missing;
- selected image list;
- recommended next action and timing;
- automation stop result.

Then set the state to closed and pause/delete the temporary high-frequency automation.
