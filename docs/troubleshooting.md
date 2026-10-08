# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Configure DATA_HOST in .env` | placeholder left | set the host |
| `Image registry is not in ALLOWED_HOSTS` | registry not listed | add it or leave `ALLOWED_HOSTS` blank |
| `Could not pull image` | wrong reference or no registry access | `docker pull <ref>` by hand |
| `Redis image not built yet` | `preflight`/`install --from preflight` without a build | `./datactl build` |
| Redis build: `groupadd: GID already in use` | `REDIS_UID` taken in the base | pick a free uid (default 1001) |
| Redis unhealthy with `redislabs/redis` | Redis Enterprise, not Redis | use the RPM build (default) |
| Elasticsearch: `must have file permissions 400 or 600` | old render; secrets not staged per service | `git pull`, `./datactl install --from configure` |
| Elasticsearch flood-stage watermark | host disk above 95 % | free disk |
| Mongo or Elasticsearch unhealthy after `configure` | stale single-file mounts (old version) | `git pull`; new version stages in place |
| `TLS file missing: mongo.pem` | file absent in `TLS_DIR` | `cat server.key server.crt > mongo.pem` |
| Health probe `certificate verify failed` | CA lacks key identifiers or SAN missing `localhost` | reissue certs |
| ClearML `preflight` cannot authenticate | ClearML `.env` not updated from `generated/clearml.env` | re-copy the lines |
| `SQLSERVER_SA_PASSWORD: use at least 16 letters and digits...` | supplied password lacks upper case, lower case or digits | leave it blank and let `configure` generate one |
| SQL Server logs `Password validation failed` | SA password does not meet SQL Server's policy | same as above; the generated passwords always comply |
| `SQL Server has no full-text search (IsFullTextInstalled=0)` | running an image built without the FTS package | `./datactl build`, then `./datactl install --from install` |
| Init logs `Full-Text Search is not installed in this SQL Server image.` | same cause, caught by `02-fulltext-catalog.sql` | as above |
| SQL Server build: `Could not resolve packages.microsoft.com` | no route to the Microsoft package repository | set `HTTP_PROXY`/`HTTPS_PROXY`; `build` passes both into the image build |
| SQL Server build: apt or curl `certificate verification failed` | TLS-inspecting proxy whose CA `SQLSERVER_IMAGE` does not trust | point `SQLSERVER_IMAGE` at an image carrying your private CA (as `lean-infrastructure` does with its trust-wrapped base) |
| `sqlserver` container exits seconds after start | host memory below ~2 GB, or `SQLSERVER_MEMORY_LIMIT_MB` set too low | free memory; `preflight` prints a note |
| `install` times out waiting for `sqlserver` | first start after an engine upgrade sits in script upgrade mode | `docker logs -f data-services-sqlserver-1`, wait for `Initialization complete.`, then `./datactl install --from install` |
| SQL Server logs a TLS certificate or key error | key is encrypted or not PKCS#8, or not readable by uid 10001 | re-issue the key unencrypted in PKCS#8, then `./datactl install --from configure` |
| Edited `init/sqlserver/*.sql` had no effect | that file's marker already exists in the volume | `docker exec data-services-sqlserver-1 rm /var/opt/mssql/.init-done/<file>`, then `./datactl restart -s sqlserver` |
| `Nothing to start: run ./datactl install first` | `start` was used before the containers existed | `./datactl install` |
| `--service does not apply to <command>` | `-s` passed to a whole-stack command such as `bundle` | drop the flag |

## Useful commands

```sh
./datactl status
docker logs data-services-elasticsearch-1 --tail 50
docker logs data-services-mongo-1 --tail 50
docker logs data-services-redis-1 --tail 50
docker logs data-services-sqlserver-1 --tail 50
docker inspect --format '{{json .State.Health.Log}}' data-services-redis-1
docker compose --project-directory . --env-file .env --env-file generated/compose.env -f compose.yaml config
```
