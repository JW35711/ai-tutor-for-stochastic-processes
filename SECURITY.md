# Security policy

## Scope

The current repository is a single-process portfolio demonstration. It has
input validation, request IDs, security headers, structured logs, an in-memory
rate limiter and an unprivileged container, but it does not yet include user
authentication or multi-tenant authorization.

Do not expose it publicly without the checklist in `docs/DEPLOYMENT.md`.

## Reporting

Please report a suspected vulnerability privately to the repository owner
instead of opening an issue that contains API keys, learner records, exploit
payloads or other sensitive data. Include the affected commit, endpoint and a
minimal reproduction without real learner information.

## Secrets

`.env`, local reference material, SQLite artifacts and reviewed vendor
snapshots are excluded from version control. Rotate a provider key immediately
if it is ever committed or printed. The health endpoint must never return keys,
prompts or learner records.
