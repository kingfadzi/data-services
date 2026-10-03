# Configuration (`.env`)

Literal values, mode 600. `CHANGE_ME` stops `configure`. Write `$` as `$$`.

## Images

| Key | Required | What to put |
|---|---|---|
| `ELASTIC_IMAGE` | yes | `<nexus>/elasticsearch/elasticsearch:8.17.2` (official image) |
| `MONGO_IMAGE` | yes | `<nexus>/library/mongo:8.0.11` (official image) |
| `BASE_IMAGE` | yes | blessed EL9 base; toolbox for rendering and base of the Redis image |
| `REDIS_PACKAGE` | yes | RPM spec from the base's repos, unpinned: `redis` or `@redis:7` |
| `REDIS_IMAGE` | yes | tag for the built Redis image, never pushed: `data-services/redis:el9-1` |
| `ALLOWED_HOSTS` | no | registries allowed for pulls; blank disables |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` | no | proxy for the Redis build; blank means none |
| `BUILD_NETWORK` | no | `default` |

Pulled images need a versioned tag. Do not use Redis Enterprise (`redislabs/redis`); it is a different product.

## Network

| Key | What to put |
|---|---|
| `DATA_HOST` | hostname or IP clients use; goes into `generated/clearml.env` |
| `BIND_ADDRESS` | `0.0.0.0` or an interface |
| `ELASTIC_PORT`, `MONGO_PORT`, `REDIS_PORT` | 9200, 27017, 6379 |
| `ELASTIC_HEAP` | JVM heap, e.g. `1g` |

## Credentials

| Key | What to put |
|---|---|
| `ELASTIC_PASSWORD`, `MONGO_ROOT_PASSWORD`, `MONGO_PASSWORD`, `REDIS_PASSWORD` | blank = generated once, kept in `generated/credentials.json` |
| `MONGO_ROOT_USERNAME` | admin user created by the Mongo image (`admin`) |
| `MONGO_USERNAME` | ClearML user (`clearml`) |

Changing a password after first start is refused; rotate in the database first.

## TLS

| Key | What to put |
|---|---|
| `TLS_ENABLED` | `true` / `false`, all three services together |
| `TLS_DIR` | directory with `ca.pem`, `server.crt`, `server.key`, `mongo.pem` |
| `ELASTIC_UID`, `MONGO_UID`, `REDIS_UID` | uids the services run as; secrets and TLS files are staged with this ownership (1000, 999, 1001) |
