# Backup, restore, and integrity drill

This drill restores into a new disposable database. It never overwrites the active database.

1. Record the migration head, UTC cutoff, row counts, object-manifest hash, and operator token.
2. Run `pg_dump --format=custom --no-owner --file pulse109.dump "$SOURCE_DATABASE_URL"` using a
   secret-injected URL. Store the dump in the approved encrypted backup location.
3. Create a new empty drill database and run
   `pg_restore --exit-on-error --no-owner --dbname "$DRILL_DATABASE_URL" pulse109.dump`.
4. Point `PULSE109_DATABASE_URL` at the drill database, run `make migrate`, then execute the
   integration and contract tests.
5. Compare source and restored counts by module, the immutable source-record hashes, latest event
   IDs, outbox/dead-letter counts, report-artifact hashes, and the Alembic head.
6. Record start/end times and evidence hashes in the release index, then remove only the explicitly
   named drill database through the approved database administration procedure.

RPO, RTO, backup frequency, retention, encryption key ownership, and the production object-store
restore command remain unset until B08/B09 are approved. A release cannot claim those targets.
