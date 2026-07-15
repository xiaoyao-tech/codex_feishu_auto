# Automation Design

Read this when choosing a scheduler, cadence, alert policy, or stop condition.

## One loop, several clocks

Do not bind every action to the same frequency.

| Clock | Purpose | Typical cadence |
|---|---|---:|
| Capture | Preserve short-lived visual evidence | 5-20 seconds |
| Patrol | Re-check sources and state | 1-60 minutes |
| Write | Persist only meaningful changes | Event-driven |
| Closeout | Rank, summarize, and stop | Fixed time or no-update threshold |

A capture can happen without a document update. A patrol can return no new signal. A write should happen only when value changes.

## Scheduler selection

### Thread heartbeat

Use for live events and overnight duty when:

- the user wants updates in the current task;
- the cadence may change during the event;
- the user may redirect the watch at any time;
- the job has a short, explicit end.

Keep one active heartbeat per watch. Merge patrol and closeout into one prompt when multiple heartbeats would overlap.

### Local Codex cron

Use for daily or weekly analytical checks when:

- the task still benefits from Codex judgment;
- local files, local lark-cli auth, or the desktop environment are needed;
- the user does not need a minute-by-minute conversation.

### Server cron or systemd

Use when:

- data, code, and credentials already live on the server;
- the task must run while the laptop is asleep;
- deterministic scripts do most of the work;
- Codex is not needed for every execution.

Use a lock such as `flock` to prevent overlap. Save state beside the production workflow. Verify schedule, output, state, and delivery rather than checking cron syntax alone.

## Cadence changes

For live events, model cadence as phases:

1. `setup`: manual test and source validation.
2. `warmup`: 10-30 minute patrol.
3. `live`: 1-5 minute patrol.
4. `verification`: 5-15 minute follow-up for official docs and corrections.
5. `closeout`: no normal patrol; rank facts, angles, and gaps.
6. `closed`: automation is paused or deleted.

For topic duty, use 30-60 minutes by default and 15 minutes only when signal rises. For ops checks, daily or weekly is usually enough.

## Stop conditions

Every temporary automation needs all of these:

- an end time or event-end test;
- a no-update threshold when appropriate;
- a closeout payload;
- an explicit pause/delete action;
- a manual stop path.

Do not silently delete a long-running production cron. Temporary thread heartbeats can be removed after closeout when the user requested a bounded watch.

## Low-noise policy

When nothing changes:

- say which major sources were checked;
- state the next watch point;
- use one or two sentences;
- do not rewrite the same candidate list;
- do not ring again for an already acknowledged event.

Strong alerts should correspond to a decision: stop current work, change publishing order, investigate an outage, or approve a high-impact action.
