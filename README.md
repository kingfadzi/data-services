# data-services

- Single-host Docker Compose stack: Elasticsearch, MongoDB and Redis for ClearML, running the official vendor images.
- Images are pulled from the configured registry (Nexus upstream, public registries in the lab); nothing is built.
- Host needs only bash, coreutils and the docker CLI. `datactl` is a bash script; configuration rendering and TLS staging run in a toolbox container.
- `compose.yaml` is static and interpolated from `.env` plus `generated/compose.env`.
- Verified versions: Elasticsearch 8.17.2, MongoDB 8.0.11, Redis 8.0.2.

## Setup

- Copy `.env.example` to `.env`. Literal values, mode 600. Write `$` as `$$` because Compose interpolates `.env`.
- `ELASTIC_IMAGE`, `MONGO_IMAGE`, `REDIS_IMAGE`: full references incl. registry and tag. Pulled when not present locally. `:latest` is rejected.
- `TOOLBOX_IMAGE`: any image with `python3` and `sh` (an EL9 base works). Used for rendering and TLS staging only.
- `ALLOWED_HOSTS`: optional allowlist of image registries; blank disables the check.
- Empty passwords are generated once into `generated/credentials.json`. Re-running `configure` with a different password is refused.
- `MONGO_ROOT_USERNAME`/`MONGO_ROOT_PASSWORD`: MongoDB administrator created by the official image on first start. `MONGO_USERNAME`/`MONGO_PASSWORD`: the ClearML user, created by `init/mongo-init.js` on first start.

```sh
./datactl configure     # render generated/ (secrets, configs, compose.env); stage TLS files
./datactl pull          # pull the three images if missing
./datactl preflight     # configure + pull + vm.max_map_count >= 262144 + compose model check
./datactl install
./datactl verify        # container health status
./datactl status
```

- `generated/clearml.env` holds the ClearML connection keys. Copy them into the ClearML `.env` (replace existing keys).
- `docker compose --project-directory . --env-file .env --env-file generated/compose.env -f compose.yaml ...` is what `datactl` runs.
- Named volumes `data-services_elasticsearch-data`, `data-services_mongo-data`, `data-services_redis-data` persist independently. Never `down -v` on a populated deployment.

## How the official images are configured

- Elasticsearch: rendered `elasticsearch.yml` mounted over the image's config; `ELASTIC_PASSWORD_FILE` points at the generated secret; single node, security on, transport TLS off.
- MongoDB: `mongod --bind_ip_all --auth` plus TLS arguments from `compose.env`; root user from `MONGO_INITDB_ROOT_*_FILE`; ClearML user and roles (`readWrite`/`dbAdmin` on `backend` and `auth`, `clusterMonitor`) from the init script. Init runs only on an empty volume.
- Redis: `redis-server /run/config/redis.conf` with the rendered config; AOF on, password required, TLS-only port when enabled.
- Secrets and config files under `generated/` are mode 644 so the image service users (uid 1000 and 999) can read them; `generated/` itself is mode 700.
- Health checks run the vendor tools inside each container: `curl` for Elasticsearch, `mongosh` for MongoDB, `redis-cli` for Redis.

## TLS

- Set `TLS_ENABLED=true`. Put `ca.pem`, `server.crt`, `server.key` and `mongo.pem` (key + cert) in `TLS_DIR`. Keep the CA key elsewhere.
- Server certificate SANs must include `localhost` (health checks) and `DATA_HOST` (clients). Certificates need subject and authority key identifiers.
- `configure` copies the files into `generated/tls/<service>/` owned by each service user (`ELASTIC_UID`, `MONGO_UID`, `REDIS_UID`; defaults match the official images). After changing certificates, run `configure` and restart the containers.
- Clients must trust the CA. For ClearML, include it in the CA bundle zip behind its `TLS_CA_BUNDLE_URL` and rebuild.

## Tests

- `python3 -m unittest discover -s tests -q` on a development host (render logic, bash syntax, compose model). Not needed on the locked-down host.

## Transfer

- `./datactl bundle` writes `dist/images.tar`, `dist/installer.tar.gz`, `dist/checksums.sha256`. Credentials, TLS files and data are excluded.
- On the target: `./datactl load [--archive PATH]` verifies `checksums.sha256` next to the archive, then loads images. Restore `.env`, `generated/credentials.json` and TLS files, then `configure` and `install`.

## Limitations

- Single node, no clustering or HA.
- No backup automation; use vendor tools before upgrades.
- No firewall; publish the database ports only to intended clients.
- Credential rotation is a manual database operation followed by updating `generated/credentials.json`.
- Changing image versions on an existing volume follows the vendors' upgrade rules; Elasticsearch does not support downgrades.
