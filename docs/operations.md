# Operations

Chain: `configure` → `pull` → `build` → `preflight` → `install` → `verify`. `--from STEP` starts later.

## Change `.env`

| Changed | Run |
|---|---|
| ports, `DATA_HOST`, `ELASTIC_HEAP` | `./datactl install --from configure`, then update the ClearML `.env` from `generated/clearml.env` |
| TLS files or `TLS_ENABLED` | `./datactl install --from configure`, then `docker compose -p data-services restart` |
| `REDIS_PACKAGE`, `BASE_IMAGE` | `./datactl install` |

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

## Volumes and backup

- `data-services_elasticsearch-data`, `data-services_mongo-data`, `data-services_redis-data`.
- Back up with vendor tools (`mongodump`, Elasticsearch snapshots, Redis AOF copy) before upgrades.
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
