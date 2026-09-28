# Public deployment

How to put the demo profile behind a domain over HTTPS, on an Ubuntu VPS.

This deploys the **demo profile**. The municipal records are synthetic. The
application, PostgreSQL, outbox, worker and audit trail are real. Do not present
this as a pilot: a pilot needs an approved regional adapter, a real identity
provider and approved retention, which are external blockers B07, B08 and B10.

## What reaches the internet

Only the proxy, on 80 and 443. PostgreSQL, the API, the worker, the inference
process and the adapters publish no ports in this overlay. Ports that are
convenient locally become an open database on a public IP, which is how demo
servers get found.

## Before you start

- A domain with an `A` record pointing at the VPS. Caddy requests the
  certificate itself, and that fails until DNS resolves.
- Ports 80 and 443 reachable. Caddy needs 80 for the ACME challenge even though
  it serves on 443.
- Docker Engine and the Compose plugin on the host.

## 1. Get the code and the secrets in place

```bash
git clone https://github.com/BAITC-Hacks/hack-803e2c8f-baash.git pulse109
cd pulse109
cp .env.example .env
```

Edit `.env` on the server. It is in `.gitignore` and must stay there.

```bash
PULSE109_PUBLIC_DOMAIN=your.domain
POSTGRES_PASSWORD=<generate one, do not reuse the local value>

# Object storage. Leave local to keep using a volume.
PULSE109_OBJECT_STORAGE_MODE=s3
PULSE109_OBJECT_STORAGE_BUCKET=<bucket>
PULSE109_OBJECT_STORAGE_ENDPOINT=<endpoint, if not AWS>
PULSE109_OBJECT_STORAGE_REGION=<region>

AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
```

Lock it down. Anyone who can read this file can read the bucket.

```bash
chmod 600 .env
```

Two rules worth stating plainly. Credentials are not settings, so nothing in
`services/core/src/pulse109/config.py` can carry one. And `.env` never goes into
Git, no matter how convenient it looks during a demo.

## 2. Build with the S3 extra

The SDK is an optional dependency, so an image that talks to S3 has to ask for
it. If `PULSE109_OBJECT_STORAGE_MODE=s3` and the extra is missing, the
application refuses at startup with a clear message rather than writing evidence
to a container filesystem that disappears on the next deploy.

```bash
docker compose \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.demo.yml \
  -f infra/compose/docker-compose.public.yml \
  build --build-arg PULSE109_EXTRAS=s3
```

## 3. Start

```bash
docker compose \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.demo.yml \
  -f infra/compose/docker-compose.public.yml \
  up -d
```

Migrations run before the API starts, as they do locally. Watch the first
certificate being issued:

```bash
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.demo.yml \
  -f infra/compose/docker-compose.public.yml logs -f proxy
```

## 4. Seed the city

The demo world is built through the same HTTP endpoints an operator uses, so it
has to run against the running API:

```bash
uv run python scripts/demo_runtime.py seed
```

## 5. Verify from somewhere else

Not from the server. A deployment that only works from the machine it runs on
has not been tested.

```bash
curl -fsS https://your.domain/api/health
curl -fsS -H "X-Region-Id: ALA" https://your.domain/api/core/health/ready
```

Then open `https://your.domain` on a phone, on mobile data rather than the
office network, and walk the demo. Refresh the page and confirm the state
survived, which proves PostgreSQL rather than a browser session.

## 6. Confirm the database is not exposed

From your laptop, not the server:

```bash
nc -vz your.domain 5432
```

A refused connection is the correct result. A successful one means the overlay
is not in the command line.

## Updating

```bash
git pull
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.demo.yml \
  -f infra/compose/docker-compose.public.yml \
  up -d --build
```

The demo volumes survive. To return to a clean city, run
`uv run python scripts/demo_runtime.py reset` and then start again.

## Resetting in public

`reset` destroys the demo data. Do not expose it. Nothing in the web interface
calls it, and it should stay that way: a public reset button is a public delete
button.

## What this deployment still is not

- No identity provider. The actor is labelled `development` and the interface
  says so.
- No live regional integration. Delivery goes to the replay adapter.
- The malware scanner is a mock. It must never be described as antivirus.
- No approved taxonomy or retention. The intake policies are synthetic.
