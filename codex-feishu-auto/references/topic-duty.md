# Topic Duty Workflow

Use this for overnight topic scouting, news patrols, competitor monitoring, and morning editorial handoff.

## Inputs

Prefer a deterministic collector that returns normalized JSON. If none exists, configure multiple source URLs and let Codex collect them with available tools.

A useful candidate object contains:

```json
{
  "id": "stable-source-id",
  "title": "...",
  "url": "...",
  "source": "...",
  "published_at": "...",
  "priority_score": 0.0,
  "urgency": "normal",
  "entities": []
}
```

Mark normalized candidates as seen even when they are not selected. This prevents a weak repeated item from reappearing forever.

## Second-pass scoring

Score the editorial value after machine filtering:

| Dimension | Suggested weight |
|---|---:|
| Domain relevance | 30% |
| Reader interest | 25% |
| Writeability | 20% |
| Timeliness | 15% |
| Uniqueness | 10% |

For every recommended item answer:

- Why write now?
- What is the non-obvious angle?
- What form fits: quick news, technical depth, business insight, or practical tool?
- What source or test is missing?

## Alerts

Strong alerts are appropriate for:

- a major model, product, API, pricing, open-source, policy, or commercial event;
- a critical outage or reversal;
- a high composite score with strong writeability;
- a signal that changes today's publishing order.

Do not keep ringing for supporting details that do not change the ranking.

## Duty log

Each useful checkpoint should append only 1-3 items:

```markdown
### YYYY-MM-DD HH:MM
- Title and link
- Score and source level
- Angle and why now
- Strong alert: yes/no
- Missing evidence
```

`state.json` is machine memory. `duty_log.md` is editorial memory. Keep both.

## No-update output

Use a compact message:

```text
No new high-signal topic this round. Current best: [...]. Next watch: [...].
```

Do not produce a fresh TOP10 when nothing changed.

## Morning closeout

At the configured closeout time:

1. Stop normal patrol.
2. Read the full duty log and state.
3. Optionally collect a wider final window.
4. Select TOP1 and TOP2-3.
5. For TOP1 provide title direction, core thesis, structure, missing evidence, and recommended publish time.
6. Alert only if TOP1 still needs an immediate decision.
7. Pause/delete the bounded automation.
