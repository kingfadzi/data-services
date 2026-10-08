# Install

Run from the `data-services` root.

## 1. Configure

```sh
cp .env.example .env && chmod 600 .env
```

Required edits:

```sh
ELASTIC_IMAGE=<nexus>/elasticsearch/elasticsearch:8.17.2
MONGO_IMAGE=<nexus>/library/mongo:8.0.11
SQLSERVER_IMAGE=<nexus>/mssql/server:2022-CU20-ubuntu-22.04
BASE_IMAGE=<nexus>/mirror/almalinux:9
DATA_HOST=<this host, reachable from the ClearML host>
```

Leave passwords blank; they are generated once into `generated/credentials.json`.

Optional TLS:

```sh
TLS_ENABLED=true
# files in config/tls/: ca.pem server.crt server.key mongo.pem (key+cert)
# SANs: localhost and DATA_HOST
```

## 2. Install

```sh
./datactl install
```

Steps printed: `configure`, `pull`, `build`, `preflight`, `install`. First run builds the Redis and SQL Server images (a few minutes).

SQL Server is the slow one to come up: its entrypoint waits out "script upgrade mode" before applying
`init/sqlserver/*.sql`, so the first `install` can sit at `--wait` for several minutes. Watch it with
`docker logs -f data-services-sqlserver-1`.

## 3. Verify

```sh
./datactl verify
```

```
elasticsearch: healthy
mongo: healthy
redis: healthy
sqlserver: healthy
sqlserver: full-text search installed
```

## 4. Hand over to ClearML

```sh
cat generated/clearml.env
```

Paste these lines over the matching keys in the ClearML `.env`.

## 5. Hand over SQL Server

```sh
cat generated/sqlserver.env
```

Host, port, database, login and a JDBC URL. The host is `DATA_HOST`, never `sqlserver` — that name
resolves only inside the Compose network.

## Notes

- No sysctl needed. A low `vm.max_map_count` switches Elasticsearch to non-mmap storage automatically.
- Do not run `docker compose down -v`; it deletes the databases.
- SQL Server needs roughly 2 GB of memory to start; `preflight` prints a note below that.
