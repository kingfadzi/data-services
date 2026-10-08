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
| `SQLSERVER_IMAGE` | yes | vendor SQL Server image, the FTS build base: `<nexus>/mssql/server:2022-CU20-ubuntu-22.04`; see the note below |
| `SQLSERVER_FTS_IMAGE` | yes | tag for the built SQL Server image, never pushed: `data-services/sqlserver:2022-fts-1` |
| `ALLOWED_HOSTS` | no | registries allowed for pulls; blank disables |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` | no | proxy for the Redis and SQL Server builds; blank means none |
| `BUILD_NETWORK` | no | `default` |

Pulled images need a versioned tag. Do not use Redis Enterprise (`redislabs/redis`); it is a different product.

Full-Text Search is not in the vendor SQL Server image, so `build` installs `mssql-server-fts` from
`packages.microsoft.com` into `SQLSERVER_FTS_IMAGE`. `mssql-tools18` (`sqlcmd`) already ships in the image.

That build needs `packages.microsoft.com` reachable. `HTTP_PROXY`/`HTTPS_PROXY` are passed into it,
and the proxy's CA has to be trusted by `SQLSERVER_IMAGE` itself — point that key at an image that
already carries your proxy settings and private CA, the way `lean-infrastructure` builds SQL Server
from its trust-wrapped base.

## Network

| Key | What to put |
|---|---|
| `DATA_HOST` | hostname or IP clients use; goes into `generated/clearml.env` and `generated/sqlserver.env` |
| `BIND_ADDRESS` | `0.0.0.0` or an interface |
| `ELASTIC_PORT`, `MONGO_PORT`, `REDIS_PORT`, `SQLSERVER_PORT` | 9200, 27017, 6379, 1433 |
| `ELASTIC_HEAP` | JVM heap, e.g. `1g` |
| `SQLSERVER_EDITION` | `MSSQL_PID`: `Developer` (free, non-production), `Express`, `Standard`, `Enterprise` or a key |
| `SQLSERVER_MEMORY_LIMIT_MB` | `mssql-conf memory.memorylimitmb`; SQL Server needs ~2 GB to start |
| `SQLSERVER_DB` | database created by the init scripts, with `<db>_ft` as its default full-text catalog |

## Credentials

| Key | What to put |
|---|---|
| `ELASTIC_PASSWORD`, `MONGO_ROOT_PASSWORD`, `MONGO_PASSWORD`, `REDIS_PASSWORD` | blank = generated once, kept in `generated/credentials.json` |
| `MONGO_ROOT_USERNAME` | admin user created by the Mongo image (`admin`) |
| `MONGO_USERNAME` | ClearML user (`clearml`) |
| `SQLSERVER_SA_PASSWORD`, `SQLSERVER_PASSWORD` | blank = generated once; SQL Server rejects a password that does not mix upper case, lower case and digits |
| `SQLSERVER_USERNAME` | login created in `SQLSERVER_DB` and made `db_owner` (`app`) |

Changing a password after first start is refused; rotate in the database first. The same applies to
`SQLSERVER_USERNAME`. Changing `SQLSERVER_DB` is not refused — it creates a second database and
leaves the first one in place.

## TLS

| Key | What to put |
|---|---|
| `TLS_ENABLED` | `true` / `false`, all four services together |
| `TLS_DIR` | directory with `ca.pem`, `server.crt`, `server.key`, `mongo.pem` |
| `ELASTIC_UID`, `MONGO_UID`, `REDIS_UID`, `SQLSERVER_UID` | uids the services run as; secrets and TLS files are staged with this ownership (1000, 999, 1001, 10001) |

SQL Server reads `server.crt` and `server.key` through the rendered `generated/mssql.conf`, which
sets `forceencryption = 1`. It requires the key unencrypted and in PKCS#8.
