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

The image runs with uid `10001`, writes learner state only below
`/app/artifacts`, and has an HTTP health check. Never commit `.env` or API
keys. Use the platform's secret manager for hosted deployments.
The server handles `SIGTERM`, stops daemon request threads and closes its SQLite
connection before the container exits.

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
