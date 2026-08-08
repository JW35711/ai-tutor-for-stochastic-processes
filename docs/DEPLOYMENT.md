# Deployment

## Local process

```bash
cp .env.example .env
python3 server.py --host 127.0.0.1 --port 8000
```

The standard-library server does not load `.env` automatically. Export only
the variables needed by the process, or use the container command below.

## Container

```bash
docker build -t stochastic-tutor-agent .
docker run --rm -p 8000:8000 \
  --env-file .env \
  -v stochastic-tutor-data:/app/artifacts \
  stochastic-tutor-agent
```

For the hardened local profile, use:

```bash
docker compose up --build
```

`compose.yaml` keeps the root filesystem read-only, drops all Linux
capabilities, enables `no-new-privileges`, bounds PID/memory/CPU use, mounts
only `/app/artifacts` for SQLite, and exposes port 8000 on loopback only.

The image runs with uid `10001`, writes learner state only below
`/app/artifacts`, and uses `/ready` for its container health check. `/live`
reports process liveness without testing dependencies. Never commit `.env` or API
keys. Use the platform's secret manager for hosted deployments.
The server handles `SIGTERM`, stops accepting work, waits for active request
threads and then closes SQLite. Accepted sockets default to a 10-second timeout
so an idle client cannot block shutdown indefinitely; configure this with
`REQUEST_SOCKET_TIMEOUT_SECONDS`.

## Required persistence

SQLite is appropriate for the single-process interview deployment. Set
`TUTOR_MEMORY_PATH` to a location on a mounted volume. Do not run multiple
independent containers against the same SQLite file over a network filesystem.
For horizontal scaling, replace learner memory with a transactional service
database and move the rate limiter to a shared store.

`MEMORY_RETENTION_DAYS=0` keeps local sessions until the learner resets them.
For a hosted demo, set a positive day count; startup then removes whole sessions
whose last update is older than that period and reports the count in `/health`.
This convenience policy does not replace a reviewed organizational retention
and backup policy.

`MAX_SESSION_EVENTS=1000` caps stored simulation turns and quiz attempts
independently for each learner. When a learner reaches the configured cap, the
oldest event of the same type is removed; other sessions are not affected.

`API_RATE_LIMIT_CLIENT_CAP=10000` bounds the number of active client keys held
by the in-process rate limiter. Expired keys are removed when capacity is
needed; a new key receives `429` if every slot is still active.

## Public exposure checklist

Before exposing the application beyond a private demo:

1. put TLS and an authenticated reverse proxy in front of the server;
2. restrict trusted hosts and request origins at the proxy;
3. store model and embedding keys in a secret manager;
4. define retention and deletion rules for learner records;
5. export logs and metrics without question text or learner identifiers;
6. run numerical, Agent and retrieval evaluations for the release commit.

The current server deliberately avoids claiming multi-tenant production
readiness. It provides request protection and observability suitable for a
single-instance portfolio demonstration.
