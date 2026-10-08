# data-services

Elasticsearch, MongoDB and Redis for ClearML, plus SQL Server with Full-Text Search, on one host with Docker Compose. Elasticsearch and MongoDB are the official images pulled from your registry; Redis is built from the RPM in your base image, and SQL Server is the vendor image with the FTS package added. Host needs bash, coreutils and docker only.

## Quickstart

```sh
git clone <gitlab>/staging/data-services.git && cd data-services
cp .env.example .env && chmod 600 .env
# edit .env: ELASTIC_IMAGE, MONGO_IMAGE, SQLSERVER_IMAGE, BASE_IMAGE, DATA_HOST (TLS optional)
./datactl install
./datactl verify
cat generated/clearml.env     # paste into the ClearML .env
cat generated/sqlserver.env   # SQL Server connection settings
```

## Docs

- [Install](docs/install.md): steps with expected output.
- [Configuration](docs/configuration.md): every `.env` key.
- [Operations](docs/operations.md): TLS, credentials, volumes, transfer.
- [Troubleshooting](docs/troubleshooting.md): symptom, cause, fix.

## Commands

Chain (each runs every earlier step): `configure` `pull` `build` `preflight` `install` `verify`.
Standalone: `status` `bundle` `load` `mongo-restore`. Options: `--env FILE`, `--from STEP`, `--archive PATH`.

## Tests

```sh
python3 -m unittest discover -s tests -q     # development host only
```
