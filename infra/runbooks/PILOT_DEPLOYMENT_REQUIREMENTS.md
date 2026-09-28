# Pilot deployment requirements

This is a requirements and verification runbook, not a deployment record. No
VPS, domain, certificate, identity provider, bucket, regional credential, RPO,
RTO, retention value, or production performance claim is supplied by this
repository. Those inputs remain blockers B07, B08 and B10.

## Preconditions owned outside this repository

- A target network and host profile, DNS name and TLS certificate lifecycle.
- PostgreSQL, object-storage and backup credentials held outside source control.
- Approved OIDC issuer, audience and JWKS endpoint, plus role and region claim
  mapping. The API accepts `roles`, `realm_access.roles`, and `regions`,
  `region_ids`, or `region_id`; every authenticated request is then checked for
  role and region scope.
- Privacy/legal basis and retention decision before any non-synthetic appeal or
  attachment enters the runtime.
- A named regional API sandbox and credentials before replacing replay delivery.

## Configuration boundary

Set approved values only through deployment secret management:

```dotenv
PULSE109_ENVIRONMENT=pilot
PULSE109_PROFILE=pilot
PULSE109_DATABASE_URL=<managed outside repository>
PULSE109_LOCAL_IDENTITY_ENABLED=false
PULSE109_OIDC_ISSUER=<approved issuer>
PULSE109_OIDC_AUDIENCE=<approved audience>
PULSE109_OIDC_JWKS_URL=<approved JWKS endpoint>
PULSE109_OIDC_ALGORITHMS=["RS256"]
PULSE109_APPROVED_LEGAL_BASIS=<approved value>
PULSE109_APPROVED_RETENTION_CLASS=<approved value>
```

`PULSE109_LOCAL_IDENTITY_ENABLED=false` is mandatory outside local, test and
demo profiles. Missing OIDC configuration fails closed with
`identity_provider_not_configured`; a missing bearer token fails with
`authentication_required`.

## Object storage boundary

Current attachment and replay-snapshot storage is filesystem-backed. S3 or an
S3-compatible implementation is **not integrated** and must not be represented
as available. Attachments already retain immutable object references, SHA-256,
media metadata and owner appeal references in PostgreSQL. Before a storage
adapter is accepted, it must verify write/read/restore hashes, preserve object
immutability, never log object contents, and have integration coverage against
the approved provider. The existing scanner is a mock, not antivirus.

## Release, rollback and restore procedure

1. Provision isolated pilot database and object-storage namespace. Do not use
   demo volumes or a shared integration database.
2. Apply `alembic -c services/core/alembic.ini upgrade head`; migrations are
   forward-only. Record the image digest and migration head.
3. Start Compose services with pilot secrets. Require `/v1/health/ready` to
   report PostgreSQL readiness before admitting traffic.
4. Run authenticated smoke checks for a permitted region and verify a denied
   role/region request returns `403`.
5. Before each release, take an operator-approved database backup and immutable
   object manifest. Restore into an isolated environment, check hashes and run
   the smoke flow there. No repository value claims a backup objective.
6. Roll back application images only after confirming their schema compatibility.
   Do not edit or reverse an applied migration. Use a forward repair migration
   if data shape must change.

## Exit criteria

The local Compose and demo profile remain the only executable runtime proof in
this checkout. A pilot deployment needs external owner approval and evidence
for every precondition above.
