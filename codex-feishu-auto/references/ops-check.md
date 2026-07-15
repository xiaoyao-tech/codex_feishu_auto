# Operations Check Workflow

Use this for scheduled server, application, data pipeline, and content-production checks.

## Safety posture

Start read-only. A request to inspect status does not authorize restart, deploy, delete, rotate credentials, or edit cron. If a repair is needed, report the smallest verifiable fix and ask for approval before changing production.

Mask secret-shaped values before reporting:

- API keys and values beginning with `sk-`;
- cookies and access tokens;
- webhook URLs and chat IDs;
- SSH private-key paths;
- private hostnames and IP addresses when the report will be shared publicly.

## Layered health model

Check these as separate facts:

1. **Host health**: uptime, disk, memory, failed systemd units.
2. **Service health**: containers/processes, health checks, ports, nginx.
3. **Scheduler health**: cron/systemd entries, lock state, last start.
4. **Artifact health**: expected files, sizes, timestamps, encryption, schema.
5. **Model/provider health**: primary route, fallback route, quality checks.
6. **Data health**: live production DB, last rows, crawl counts, source errors.
7. **Auth health**: public versus authenticated API behavior.
8. **Delivery health**: Feishu document/sheet/message actually arrived and can be read back.

A green container does not prove a green model path. HTTP 200 does not prove data freshness. One failed source does not prove the whole pipeline is down.

## Find production truth

Before reading a database or output file:

1. Inspect container mounts or service arguments.
2. Identify the path used by the running process.
3. Compare timestamps and sizes.
4. Query the live database read-only.
5. Cross-check with logs and authenticated API output.

Do not assume a similarly named file in the source directory is production.

## Partial failures

Examples of degraded-but-running states:

- primary model failed, fallback completed the artifact;
- one source returned 429, other sources still populated the DB;
- public API returned 401, authenticated API and DB were fresh;
- website returned 200, conversion endpoint returned 502;
- cron exists, but no current output artifact was generated.

Report these precisely. Avoid both “everything is down” and “basically normal.”

## Report format

```markdown
## Verdict
Normal / Degraded / Abnormal

## Evidence
- Service: ...
- Scheduler: ...
- Artifact: ...
- Model path: ...
- Data: ...
- Auth/delivery: ...

## Issues
- ...

## Recommended action
- ...
```

Write a compact healthy checkpoint to automation memory. Preserve enough evidence for the next run to detect change, but never store secrets.
