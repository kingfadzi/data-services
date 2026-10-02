#!/usr/bin/env python3
"""Render data-services secrets and service configuration. Runs inside a container; stdlib only, Python 3.9+."""
import json
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote


class Error(Exception):
    pass


def env_file(path):
    values = {}
    if not path.is_file():
        raise Error(f"Missing {path}; copy .env.example to .env and configure it")
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise Error(f"Invalid .env key at line {n}")
        if key in values:
            raise Error(f"Duplicate .env key: {key}")
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise Error(f"Unclosed quote at line {n}")
            value = value[1:-1]
        values[key] = value
    return values


def need(env, key):
    value = env.get(key, '')
    if not value or 'CHANGE_ME' in value:
        raise Error(f"Configure {key} in .env")
    return value


def boolean(env, key, default=False):
    value = env.get(key, str(default)).lower()
    if value not in ('true', 'false'):
        raise Error(f"{key} must be true or false")
    return value == 'true'


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(content)
    temporary.replace(path)


def write_json(path, value):
    private_write(path, json.dumps(value, indent=2) + '\n')


def render(root, env, host_root, tls_dir=None):
    """root: directory holding generated/. host_root: the same directory as seen by the Docker host.
    tls_dir: where TLS files are visible here; defaults to TLS_DIR under root."""
    generated = root / 'generated'
    generated.mkdir(exist_ok=True)
    cred_path = generated / 'credentials.json'
    old = json.loads(cred_path.read_text()) if cred_path.exists() else {}
    credentials = {}
    for key in ('ELASTIC_PASSWORD', 'MONGO_PASSWORD', 'REDIS_PASSWORD'):
        value = env.get(key, '') or old.get(key) or secrets.token_hex(32)
        if old.get(key) and value != old[key]:
            raise Error(f'{key}: rotating existing credentials requires an explicit database operation')
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,}', value):
            raise Error(f'{key}: use at least 16 letters, digits, underscores or hyphens')
        credentials[key] = value
    username = need(env, 'MONGO_USERNAME')
    if old.get('MONGO_USERNAME', username) != username:
        raise Error('Changing an initialized MongoDB username requires an explicit database operation')
    credentials['MONGO_USERNAME'] = username
    write_json(cred_path, credentials)
    for key, filename in (('ELASTIC_PASSWORD', 'elastic_password'), ('REDIS_PASSWORD', 'redis_password')):
        private_write(generated / filename, credentials[key])
    write_json(generated / 'mongo_credentials', {'username': username, 'password': credentials['MONGO_PASSWORD']})

    tls = boolean(env, 'TLS_ENABLED')
    tls_setting = need(env, 'TLS_DIR')
    host_tls = Path(tls_setting) if tls_setting.startswith('/') else Path(host_root) / tls_setting
    if tls:
        check = Path(tls_dir) if tls_dir else root / tls_setting
        for filename in ('ca.pem', 'server.crt', 'server.key', 'mongo.pem'):
            if not (check / filename).is_file():
                raise Error(f'TLS file missing: {filename}')
        tls_mount = host_tls
    else:
        (generated / 'no-tls').mkdir(exist_ok=True)
        tls_mount = Path(host_root) / 'generated' / 'no-tls'

    es = {'cluster.name': 'clearml', 'node.name': 'clearml-data', 'network.host': '0.0.0.0',
          'discovery.type': 'single-node', 'path.data': '/usr/share/elasticsearch/data',
          'path.logs': '/usr/share/elasticsearch/logs', 'xpack.security.enabled': True,
          'xpack.security.enrollment.enabled': False, 'xpack.security.http.ssl.enabled': tls,
          'xpack.security.transport.ssl.enabled': False}
    if tls:
        es.update({'xpack.security.http.ssl.key': 'tls/server.key', 'xpack.security.http.ssl.certificate': 'tls/server.crt',
                   'xpack.security.http.ssl.certificate_authorities': ['tls/ca.pem']})
    write_json(generated / 'elasticsearch.yml', es)
    mongo = {'storage': {'dbPath': '/data/db'}, 'net': {'bindIp': '0.0.0.0', 'port': 27017}, 'security': {'authorization': 'enabled'}}
    if tls:
        mongo['net']['tls'] = {'mode': 'requireTLS', 'certificateKeyFile': '/run/service-tls/mongo.pem',
                               'CAFile': '/run/service-tls/ca.pem', 'allowConnectionsWithoutCertificates': True}
    write_json(generated / 'mongod.json', mongo)
    redis = ['bind 0.0.0.0', 'protected-mode yes', 'dir /data', 'appendonly yes', f'requirepass {credentials["REDIS_PASSWORD"]}']
    redis += (['port 0', 'tls-port 6379', 'tls-cert-file /run/service-tls/server.crt', 'tls-key-file /run/service-tls/server.key',
               'tls-ca-cert-file /run/service-tls/ca.pem', 'tls-auth-clients no'] if tls else ['port 6379'])
    private_write(generated / 'redis.conf', '\n'.join(redis) + '\n')
    scheme = 'https' if tls else 'http'
    private_write(generated / 'elastic-health.conf',
                  f'url = "{scheme}://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=3s"\n'
                  f'user = "elastic:{credentials["ELASTIC_PASSWORD"]}"\n' + ('cacert = "/run/tls/ca.pem"\n' if tls else ''))
    # Service daemons read these; the directory itself stays private.
    generated.chmod(0o700)
    for name in ('elasticsearch.yml', 'mongod.json', 'redis.conf'):
        (generated / name).chmod(0o644)
    # Values compose.yaml needs beyond .env.
    private_write(generated / 'compose.env', f'TLS_MOUNT_DIR={tls_mount}\n')

    host = need(env, 'DATA_HOST')
    query = 'authSource=admin' + ('&tls=true&tlsCAFile=/etc/pki/tls/certs/ca-bundle.crt' if tls else '')
    user = quote(username, safe='')
    password = quote(credentials['MONGO_PASSWORD'], safe='')
    values = {'MONGO_BACKEND_URI': f'mongodb://{user}:{password}@{host}:{need(env, "MONGO_PORT")}/backend?{query}',
              'MONGO_AUTH_URI': f'mongodb://{user}:{password}@{host}:{need(env, "MONGO_PORT")}/auth?{query}',
              'ELASTICSEARCH_URLS': f'{scheme}://{host}:{need(env, "ELASTIC_PORT")}',
              'ELASTICSEARCH_USERNAME': 'elastic', 'ELASTICSEARCH_PASSWORD': credentials['ELASTIC_PASSWORD'],
              'REDIS_HOST': host, 'REDIS_PORT': need(env, 'REDIS_PORT'), 'REDIS_PASSWORD': credentials['REDIS_PASSWORD'],
              'REDIS_TLS': str(tls).lower()}
    private_write(generated / 'clearml.env', '\n'.join(f'{key}={value}' for key, value in values.items()) + '\n')


def main():
    work = Path(sys.argv[1] if len(sys.argv) > 1 else '/work')
    host_root = os.environ.get('HOST_ROOT')
    if not host_root:
        raise Error('HOST_ROOT must hold the data-services directory path on the Docker host')
    tls_dir = work / 'tls' if (work / 'tls').is_dir() else None
    render(work, env_file(work / '.env'), host_root, tls_dir)
    print('Rendered generated/; connection settings: generated/clearml.env (secret)')


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError) as error:
        print(f'Error: {error if isinstance(error, Error) else type(error).__name__}', file=sys.stderr)
        sys.exit(1)
