# Operations

Chain: `configure` → `pull` → `build` → `preflight` → `install` → `verify`. `--from STEP` starts later.

## Change `.env`

| Changed | Run |
|---|---|
| ports, `DATA_HOST`, `ELASTIC_HEAP` | `./datactl install --from configure`, then update the ClearML `.env` from `generated/clearml.env` |
| TLS files or `TLS_ENABLED` | `./datactl install --from configure`, then `docker compose -p data-services restart` |
| `REDIS_PACKAGE`, `BASE_IMAGE`, `SQLSERVER_IMAGE` | `./datactl install` |
| `SQLSERVER_EDITION`, `SQLSERVER_MEMORY_LIMIT_MB` | `./datactl install --from configure`, then `docker compose -p data-services restart sqlserver` |

Re-running `configure` on a live stack is safe; staged files are overwritten in place.

## TLS

- Server cert SANs: `localhost` and `DATA_HOST`. Include subject and authority key identifiers.
- `mongo.pem` = `server.key` + `server.crt` concatenated.
- Keep the CA key outside `TLS_DIR`.
- ClearML must trust the CA: put it in the CA bundle zip behind ClearML's `TLS_CA_BUNDLE_URL`.

## Credentials

- `generated/credentials.json` is the source of truth; back it up.
- Mongo admin: `MONGO_ROOT_USERNAME` / `MONGO_ROOT_PASSWORD` from that file.
- Rotation: change in the database with the vendor tools, then edit `credentials.json`, then `./datactl install --from configure`.

## Restore a MongoDB dump (any database)

Hydrate a database from a `mongodump` output, for ClearML or any other application sharing this MongoDB.

```sh
./datactl mongo-restore --dump /path/to/dumpdir                      # everything in the dump
./datactl mongo-restore --dump /path/to/dumpdir --db sales --drop    # one database, replace existing collections
./datactl mongo-restore --dump /path/to/sales.archive.gz --db sales --to-db sales_test   # archive, restore under another name
```

- `--dump`: directory from `mongodump --out` (contains `<db>/` folders) or a file from `mongodump --archive` (`.gz` handled).
- `--db`: database name inside the dump to restore (others skipped).
- `--to-db`: rename on restore; needs `--db`.
- `--drop`: drop each collection before restoring it.
- Runs `mongorestore` inside the Mongo container as the admin user; TLS handled automatically. The dump is copied in and removed afterwards.
- Application users for that database are not created; add them with `mongosh` as admin.

## SQL Server and Full-Text Search

- `SQLSERVER_FTS_IMAGE` is the vendor image plus `mssql-server-fts`. `./datactl verify` asserts
  `SERVERPROPERTY('IsFullTextInstalled') = 1`, and the container's entrypoint refuses to stay up
  without it, so a stack that is up has FTS.
- `init/sqlserver/*.sql` is applied by the entrypoint on start, one marker per file under
  `/var/opt/mssql/.init-done/` in the volume. Adding `03-something.sql` applies just that file on the
  next start; editing an already-applied file does nothing until you remove its marker.
- `SQLSERVER_DB` gets `<db>_ft` as its default full-text catalog. Per-table full-text indexes belong
  to whoever owns the schema:

  ```sql
  CREATE FULLTEXT INDEX ON dbo.docs (body) KEY INDEX PK_docs;
  ```

- Back up with `BACKUP DATABASE` inside the container; the SA password is in `generated/credentials.json`.

## Volumes and backup

- `data-services_elasticsearch-data`, `data-services_mongo-data`, `data-services_redis-data`,
  `data-services_sqlserver-data`.
- Back up with vendor tools (`mongodump`, Elasticsearch snapshots, Redis AOF copy, `BACKUP DATABASE`) before upgrades.
- Never `docker compose down -v`.

## Restart

```sh
docker compose -p data-services restart
./datactl verify
```

## Transfer

```sh
./datactl bundle                       # dist/images.tar installer.tar.gz checksums.sha256
# target:
tar -xzf installer.tar.gz && cd data-services
./datactl load --archive /path/images.tar
cp /secure/.env .; cp -r /secure/generated/credentials.json generated/
./datactl install --from configure
```

## Version changes

- Elasticsearch does not support downgrades; new minor versions follow the vendor upgrade path.
- Redis version follows the base image's repository (`REDIS_PACKAGE` unpinned).
- SQL Server: moving `SQLSERVER_IMAGE` to a newer CU rebuilds the FTS image and upgrades the
  databases in place on first start. That upgrade is what the entrypoint's readiness streak waits
  out, so allow several minutes and do not interrupt it.
