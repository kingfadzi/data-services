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

Steps printed: `configure`, `pull`, `build`, `preflight`, `install`. First run builds the Redis image (a few minutes).

## 3. Verify

```sh
./datactl verify
```

```
elasticsearch: healthy
mongo: healthy
redis: healthy
```

## 4. Hand over to ClearML

```sh
cat generated/clearml.env
```

Paste these lines over the matching keys in the ClearML `.env`.

## Notes

- No sysctl needed. A low `vm.max_map_count` switches Elasticsearch to non-mmap storage automatically.
- Do not run `docker compose down -v`; it deletes the databases.
