[Русский](PUBLIC_DEPLOYMENT.md) · [English](PUBLIC_DEPLOYMENT.en.md) · [Қазақша](PUBLIC_DEPLOYMENT.kk.md)

# Public Demo: Deployment and Operations

Current deployment record of the [landing page](https://baash.govtech-kz.com/) and [operator workspace](https://baash.govtech-kz.com/demo), verified on **October 1, 2026**. Environment profile is `PULSE109_PROFILE=demo`: real FastAPI/PostgreSQL/migrations/audit/outbox/worker, synthetic ALA records, demonstration identities, and synthetic replay delivery receipts. Regional CRM and IdP are not connected; legal basis and data retention periods are not agreed. This is a demonstration environment.

## Verified environment on shared server

| Parameter                                  | Verified state                                                                                                                      |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| HTTPS                                      | Existing organizers' proxy; custom Caddy/80/443 are not started                                                                     |
| Compose project / directory                | `pulse109-final` / `~/pulse109-final`                                                                                               |
| Overlay                                    | base + demo + behind-proxy + VPS-local `docker-compose.vps.yml`                                                                     |
| Web                                        | GHCR image `ghcr.io/baitc-hacks/pulse109-web:22d89e7`                                                                               |
| Web digest                                 | `sha256:60b1f83d318a0df90af5fecf403217bab171295760ac1ec22f4d6d8d863af8e2`                                                           |
| Proxy upstream                             | `127.0.0.1:8009` → Next.js 3000; host port 3000 occupied by another application                                                     |
| API                                        | `127.0.0.1:8080` → API 8080; access needed for seeding/probes from host                                                             |
| PostgreSQL / worker / inference / adapters | Internal Docker network; host ports are not published                                                                               |
| Object storage                             | `local` volumes; S3 is wired in code, private bucket not verified on this VPS                                                       |
| Verification                               | Landing HTTP 200; web/API/DB ready; seven persistent services healthy                                                               |
| Restart                                    | Persistent containers `unless-stopped`; rootless Docker enabled, systemd Restart=always, Linger=yes; migrate — one-shot, restart=no |

Web is built via [publish-web workflow](../../.github/workflows/publish-web.yml), [successful run](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36741389474). Later commits `41b6a1f`/`e494390` modify documentation, so the README HEAD and web image tag differ. Every new main is not automatically deployed.

On October 1, the site returned 502: user Docker service was cleanly stopped, containers had `restart=no`. Docker and the stack were recovered; restart policies are preserved in the VPS override. `OOMKilled=false`: RAM exhaustion is not confirmed as the root cause of this failure. Unused BuildKit cache and logs from four old stopped demo containers were purged; tagged images and volumes are preserved. After stabilization, quota stands at 4083M / soft 4096M / hard 5120M. Old upload archive is preserved on the workstation with SHA verification, its duplicate removed from VPS. Headroom to the soft limit is about 13M; a new image rollout requires a dedicated capacity check. Prior to demo/refresh, repeated monitoring is required. A restart does not fix disk exhaustion or an external proxy stoppage.

## Commands specific to this environment

Execute commands in a VPS session belonging to the rootless Docker owner. Always pass `--env-file .env`: without it, Compose under nested configuration may fail to find the mandatory password. Secrets are never printed in logs and never committed to Git.

```bash
cd ~/pulse109-final
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
compose=(docker compose --env-file .env -p pulse109-final
  -f infra/compose/docker-compose.yml
  -f infra/compose/docker-compose.demo.yml
  -f infra/compose/docker-compose.behind-proxy.yml
  -f docker-compose.vps.yml)

systemctl --user is-active docker
"${compose[@]}" ps -a
df -h
quota -s || true
docker system df
```

VPS override of current environment:

```yaml
services:
  web:
    restart: unless-stopped
    image: ghcr.io/baitc-hacks/pulse109-web:22d89e7
    ports: !override
      - "127.0.0.1:8009:3000"
  core-api:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
    ports: !override
      - "127.0.0.1:8080:8080"
  worker:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
  inference:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
  open311-sandbox:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
    environment:
      PYTHONPATH: /app/adapters/open311/src
  postgres:
    restart: unless-stopped
  adapter-runtime:
    restart: unless-stopped
```

If daemon is not running, recovery without build:

```bash
systemctl --user start docker
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build
curl -fsS http://127.0.0.1:8009/api/health
curl -fsS -H 'X-Region-Id: ALA' http://127.0.0.1:8080/v1/health/ready
```

From another machine:

```bash
curl -fsS https://baash.govtech-kz.com/api/health
curl -fsS -H 'X-Region-Id: ALA' https://baash.govtech-kz.com/api/core/health/ready
```

Open landing and `/demo`, refresh the page, verify saved appeal, War Room, and Replay Lab. Availability checks above do not prove Radar freshness or private S3 operation.

## Golden World before recording

Water scenario updated on **October 1, 2026, 21:13 Asia/Qyzylorda (16:13 UTC)**, generation `20261001T161258Z`. Verified:

- 121 calendar days / 268 historical appeals: previous history preserved, two appeals added for the following day;
- six new water reports with synthetic coordinates, clustered by Radar over six hours;
- Ask Pulse RU/KK, numeric chart, provenance and underlying records;
- PDF/XLSX and 30/60/90 forecasts;
- landing, `/demo` and both health endpoints reachable from workstation; all seven services healthy.

Prior to first recording, `pg_dump -Fc` was created with 600 permissions, validated via `pg_restore --list` and SHA-256. Backup is preserved on VPS and workstation; SHA of copies matched. Previous appeals, dates, resolutions, incidents, and objects are preserved. Appending was performed via ordinary HTTP endpoints; data was not relabeled as real. Images and external proxy remained in previous configuration.

### Operator command for next presentation

`scripts/demo_refresh.py` is run only manually on the Docker host. Standard Python 3.10+ and Docker CLI are required; httpx and seed are executed by existing Python inside core-api, without installing packages or building web on the VPS.

In a normal checkout, all six modules are available side by side: `demo_refresh.py`, `demo_clock.py`, `demo_pagination.py`, `demo_runtime.py`, `demo_world.py`, and `verify_demo_world.py`. On the verified VPS, their copy from `135680a` resides separately:

```bash
cd ~/pulse109-final/stabilization-135680a
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
python3 scripts/demo_refresh.py \
  --compose-project pulse109-final \
  --backup-file "backups/pre-refresh-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

The command checks Compose labels of both containers, API/DB readiness, and `demo` profile. Any other project or profile is rejected prior to write. Backup is created exclusively: existing file is not overwritten, empty/unreadable archive aborts the process. Then missing calendar fixtures and six new water reports with `-refresh-<UTCgeneration>` suffix are appended. Previously created states and dates are preserved; fixture ID conflict with another source is rejected.

After addition, the full smoke test above is performed; cluster is persisted in Radar only after its success. On partial failure, backup and previous world are preserved. To retry the same generation within an hour, run with `--generation <printed UTCtoken>` and a **new** backup file: already created records are skipped. A fresh standard run creates the next generation. Success string is `fresh synthetic water generation: ...; existing world preserved`.

Freshness is bounded by verification time: execute prior to recording/demo. Normal `seed` does not update dates. Local `demo_runtime.py prepare/verify/reset` manage `pulse109-demo` and do not update `pulse109-final`. Reset endpoint is not published; this procedure does not delete volumes and does not change the Radar window.

## Upgrade and rollback

Before switching: check quota, create a backup of DB/object manifest, record digest of current images, and verify schema compatibility. Web is built in GitHub Actions, published with an immutable SHA tag, and pulled after a successful workflow. For private GHCR, use a token with `read:packages` via `password-stdin` and temporary Docker auth configuration. Secret must never enter command history or repository.

After pulling candidate, replace the web tag in VPS override, validate Compose, and execute `up -d --no-build web`. Then verify accessibility and browser scenario. Backend images are updated separately with verified migrations and contracts. Rollback preserves previous images and compatible schema; applied migrations are never edited.

On quota shortage, first inspect `docker system df` and named resources. Unused build cache can be purged via `docker builder prune --all --force` inside personal rootless Docker. Do not use `docker system prune -a` on shared server; volumes, foreign resources, and rollback images are not build cache. Monitor log growth: restart policy does not configure log rotation.

## Deployment on another host

This section describes options, not the state of current VPS. A new host requires DNS/TLS, Docker/Compose, quota/capacity, private secret storage, and pre-verified ports 80/443 and loopback.

- **Existing HTTPS proxy:** base + demo + `docker-compose.behind-proxy.yml`, custom loopback port override, and corresponding upstream. By default, web port of this overlay is 3000; current environment overrides it to 8009.
- **Dedicated host without proxy:** base + demo + `docker-compose.public.yml` launches Caddy. Only here are 80/443 bound. Do not use this overlay on the verified shared VPS.
- **Storage:** `PULSE109_OBJECT_STORAGE_MODE=local` retains filesystem volumes; `s3` requires bucket/endpoint/region and credentials outside Git. Public overlay installs S3 extra. Prior to claiming private S3, verify write → SHA/read → restart → read → anonymous access denied → recovery.
- **Database:** `POSTGRES_PASSWORD` must be a unique URL-safe secret; migration/API/worker URLs are derived from it. For existing DB, environment change does not modify role password by itself.
- **Seed:** execute against ready API of corresponding demonstration project; behind-proxy API is normally not published, so use internal process or temporary loopback bind. Do not expose API publicly for seed.

Production pilot requirements — [PILOT_DEPLOYMENT_REQUIREMENTS](PILOT_DEPLOYMENT_REQUIREMENTS.en.md). [BACKUP_RESTORE](BACKUP_RESTORE.en.md) defines procedure, but not approved RPO/RTO. [Golden Demo](../../docs/GOLDEN_DEMO.en.md) defines presentation route, [FEATURE_STATUS](../../docs/FEATURE_STATUS.en.md) — current boundaries. Demonstration scanner remains mock, B07/B08/B10 open.
