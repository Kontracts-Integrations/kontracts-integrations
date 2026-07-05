-- Clean-slate the record-sync state while PRESERVING mapping templates & connections.
--
-- Clears:
--   sync_records       — per-record sync results
--   sync_runs          — run history
--   log_entries        — run/operational logs
--   id_mappings        — produced source->Kontracts ID store (all lookup buckets)
--   record_sync_state  — upsert payload hashes (create/update/skip decisions)
--
-- Preserves:
--   connections, mapping_templates, mapping_versions, lookup_tables (bucket registry)
--
-- After this, the next run re-creates every record (no dedup / no upsert skips),
-- because both id_mappings and record_sync_state are empty.
--
-- Run:  docker compose exec -T postgres \
--         psql -U postgres -d tririga_kontracts -f - < backend/scripts/clean_slate_record_sync.sql

BEGIN;

SELECT 'BEFORE'  AS phase,
       (SELECT count(*) FROM sync_runs)         AS sync_runs,
       (SELECT count(*) FROM sync_records)      AS sync_records,
       (SELECT count(*) FROM log_entries)       AS log_entries,
       (SELECT count(*) FROM id_mappings)       AS id_mappings,
       (SELECT count(*) FROM record_sync_state) AS record_sync_state;

-- All referencing tables are truncated together, so no CASCADE is needed and
-- mapping_templates / connections (referenced by, not truncated) are untouched.
-- RESTART IDENTITY resets the serial id sequences back to 1.
TRUNCATE TABLE
    sync_records,
    sync_runs,
    log_entries,
    id_mappings,
    record_sync_state
RESTART IDENTITY;

-- Optional: also reset the named-lookup-table registry. Leave commented to keep
-- declared bucket names; they re-register automatically on the next save/run.
-- TRUNCATE TABLE lookup_tables RESTART IDENTITY;

SELECT 'AFTER'   AS phase,
       (SELECT count(*) FROM sync_runs)         AS sync_runs,
       (SELECT count(*) FROM sync_records)      AS sync_records,
       (SELECT count(*) FROM log_entries)       AS log_entries,
       (SELECT count(*) FROM id_mappings)       AS id_mappings,
       (SELECT count(*) FROM record_sync_state) AS record_sync_state;

SELECT 'PRESERVED' AS phase,
       (SELECT count(*) FROM connections)       AS connections,
       (SELECT count(*) FROM mapping_templates) AS mapping_templates,
       (SELECT count(*) FROM mapping_versions)  AS mapping_versions,
       (SELECT count(*) FROM lookup_tables)     AS lookup_tables;

COMMIT;
