# data-services

Independent, single-host Docker Compose deployment for Elasticsearch, MongoDB and Redis, built on configurable AlmaLinux 9 / UBI 9 images. No upstream database container images are used. Vendor binaries come from your internal RPM repositories; this repository does not compile database engines from source.

This content is prepared for `staging/data-services`. Remote repository creation/publication and actual container builds were blocked in the development session. The default versions follow the reviewed ClearML Compose candidates (ES 8.19.9, MongoDB 8.0.15, Redis 8.2.3), but integration on these custom images still needs qualification. Supply the exact RPM package names/releases available in your internal mirror. Redis 8 is not assumed to exist in the stock EL9 repository; mirror or package it internally first. The mongosh version is separately configurable.

## Setup

Copy `.env.example` to `.env`, `config/yum.repo.example` to `config/yum.repo`, and provide `config/ca.pem`. Configure internal image references, registry host allowlist, package versions, data-host DNS and bind address/ports. Preload the runtime base image. The base needs CA trust tooling and `dnf`/`microdnf`; use full AlmaLinux 9 or UBI 9. Signatures remain enabled in the example YUM configuration; supply matching vendor signing keys through internal URLs or the base image.

Run these with Docker access:

```sh
./datactl build
./datactl configure
./datactl preflight
./datactl install
./datactl verify
./datactl status
```

`generated/compose.json` is a standard Compose file. You can also use `docker compose -f generated/compose.json up -d --pull never`. The installer does not modify the host sysctl: set `vm.max_map_count` to at least 262144 before starting Elasticsearch. Set `ELASTIC_HEAP` for your machine and provide sufficient memory/disk. Firewall the published database ports to intended clients.

Named volumes `data-services_elasticsearch-data`, `data-services_mongo-data`, and `data-services_redis-data` persist independently of containers. Do not use Compose `down -v` on a populated deployment. Entry scripts initialize volume ownership and drop to the vendor service account.

The first configure generates secrets when password fields are empty. They are retained in private `generated/credentials.json`. Copy the matching values from `generated/clearml.env` into the ClearML installer's existing `.env` keys. Protect and back up `generated/`; rerunning configure refuses password changes that would desynchronize an initialized database. Credential rotation must be performed in the database first through a controlled maintenance operation.

MongoDB initializes on loopback only, creates a ClearML user for the `backend` and `auth` databases, stops the temporary process, and starts with authentication on the network interface. Existing data without an initialization marker fails closed for operator recovery; it is never erased. This includes interrupted first initialization after WiredTiger creation: inspect the volume and users before repair.

Elasticsearch uses its built-in `elastic` account with a stable bootstrap password. Do not reset that user's password outside a coordinated credentials update. Redis requires a password and uses AOF persistence. The simple lab stack uses TCP by default; authentication does not encrypt traffic.

## TLS and portability

Set `TLS_ENABLED=true` and put `ca.pem`, `server.crt`, `server.key`, and combined MongoDB `mongo.pem` under `TLS_DIR`. The server certificate must include `localhost` for in-container health checks and `DATA_HOST` for clients. A shared certificate is sufficient for this single-host lab stack. Startup copies private keys into service-owned directories; originals remain private host files. TLS is required on all published database ports when enabled. Clients authenticate with database credentials and verify the CA; client certificates are not required.

Switch `RUNTIME_BASE_IMAGE` and the internal YUM repo file to build UBI 9 variants. Use separate output image tags and rerun the ClearML acceptance suite. Package availability is checked by the build rather than assumed from image family.

`./datactl bundle` exports runtime images and repository files without credentials or data into `dist/`. Verify checksums after transfer, restore site configuration separately, then use `./datactl load` and install. Container/base builders are not included in this runtime bundle. Restrict build/runtime public egress on the host and pre-populate internal mirrors; `BUILD_NETWORK` selects a Docker build network mode but does not enforce a firewall.

Before upgrades, back up each database using vendor backup tools and keep the previous image set and credentials. No automatic database migration/downgrade or destructive reset is provided.
