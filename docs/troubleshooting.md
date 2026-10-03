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

## Useful commands

```sh
./datactl status
docker logs data-services-elasticsearch-1 --tail 50
docker logs data-services-mongo-1 --tail 50
docker logs data-services-redis-1 --tail 50
docker inspect --format '{{json .State.Health.Log}}' data-services-redis-1
docker compose --project-directory . --env-file .env --env-file generated/compose.env -f compose.yaml config
```
