# data-services

- Single-host Docker Compose stack: Elasticsearch, MongoDB and Redis for ClearML.
- Host needs only bash, coreutils and the docker CLI. `datactl` is a bash script; secret and config rendering runs in a container from `RUNTIME_BASE_IMAGE` (python3 from the base image).
- `compose.yaml` is static and interpolated from `.env` plus `generated/compose.env`.
- Images are built from vendor RPMs on a configurable EL9 base (AlmaLinux 9 verified; UBI 9 build supported). No upstream database container images.
- Verified versions: Elasticsearch 8.19.9, MongoDB 8.0.15 with mongosh 2.5.8, Redis 8.2.10 (Remi module stream `redis:remi-8.2`). These match the clearml-server v2.4.0 compose file apart from the Redis patch level.

## Setup

- Copy `.env.example` to `.env`. Literal values, mode 600.
- `RUNTIME_BASE_IMAGE`: EL9 base, present locally, tagged from an `ALLOWED_HOSTS` registry. Also used as the toolbox for `configure`.
- `.env` values are literal; write `$` as `$$` because Compose interpolates `.env`.
- `ALLOWED_HOSTS`: registries and YUM repo hosts the build may contact.
- `YUM_REPO_FILE`: optional. Needed here in practice: Elasticsearch, MongoDB and Redis vendor repos are not in the base image. Multiple `gpgkey` URLs per section are allowed (Remi signs with more than one key).
- `*_PACKAGE`: exact RPM specs. A module stream such as `@redis:remi-8.2` is accepted.
- `CA_BUNDLE`: CA file copied into the images (writable if you append).
- Empty passwords are generated once into `generated/credentials.json`. Re-running `configure` with a different password is refused.

```sh
./datactl build
./datactl configure
./datactl preflight     # checks vm.max_map_count >= 262144, images, compose model
./datactl install
./datactl verify        # in-container authenticated health probes
./datactl status
```

- `generated/clearml.env` holds the ClearML connection keys. Copy them into the ClearML `.env` (replace existing keys).
- `docker compose --project-directory . --env-file .env --env-file generated/compose.env -f compose.yaml ...` is what `datactl` runs; use it directly if needed.
- Named volumes `data-services_elasticsearch-data`, `data-services_mongo-data`, `data-services_redis-data` persist independently. Never `down -v` on a populated deployment.

## Tests

- `python3 -m unittest discover -s tests -q` on a development host (render logic, bash syntax, compose model). Not needed on the locked-down host.

## Behaviour

- MongoDB: first start initialises the ClearML user on loopback (`readWrite`/`dbAdmin` on `backend` and `auth`, `clusterMonitor` for the API server's version check), then restarts with auth on the network port. Existing data without the init marker fails closed. No separate admin user is created.
- Elasticsearch: packaged config path `/etc/elasticsearch` is used (the RPM forces it). Install-time auto-configuration (certs, keystore, initial master) is removed at build. Keystore commands run as the service user so restarts succeed. Bootstrap password comes from the generated secret.
- Redis: AOF persistence, password required, TLS-only port when TLS is enabled.
- All entrypoints run as root only to fix ownership and copy TLS files, then drop to the vendor service account.

## TLS

- Set `TLS_ENABLED=true`. Put `ca.pem`, `server.crt`, `server.key` and `mongo.pem` (key + cert) in `TLS_DIR`. Keep the CA key elsewhere.
- Server certificate SANs must include `localhost` (health probes) and `DATA_HOST` (clients). Certificates need subject and authority key identifiers; a CA without them failed verification in the lab.
- After changing certificates, restart the containers; entrypoints copy TLS files at start.
- Clients must trust the CA. For ClearML, append it to its `config/ca.pem` and rebuild.
- Verified in the lab: health probes, ClearML preflight and SDK round trip over TLS; wrong passwords and an untrusted CA rejected.

## Transfer

- `./datactl bundle` writes `dist/images.tar`, `dist/installer.tar.gz`, `dist/checksums.sha256`. Credentials, TLS files and data are excluded.
- On the target: `./datactl load [--archive PATH]` verifies `checksums.sha256` next to the archive, then loads images. Restore `.env`, `generated/credentials.json` and TLS files, then `configure` and `install`.

## Limitations

- Single node, no clustering or HA.
- No backup automation; use vendor tools before upgrades.
- No firewall; publish the database ports only to intended clients.
- Credential rotation is a manual database operation followed by updating `generated/credentials.json`.
