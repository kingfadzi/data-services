#!/bin/bash
set -euo pipefail
if [ "${TLS_ENABLED:-false}" = true ]; then
  mkdir -p /run/service-tls
  cp /run/tls/* /run/service-tls/
  chown -R mongod:mongod /run/service-tls
  chmod 700 /run/service-tls
fi
chown -R mongod:mongod /data/db
if [ ! -f /data/db/.initialized ]; then
  if [ -e /data/db/WiredTiger ]; then
    echo 'Existing database without initialization marker; refusing to alter users. Restore marker only after verifying credentials.' >&2
    exit 1
  fi
  # Bootstrap is bound only to loopback and never uses published interfaces.
  setpriv --reuid=mongod --regid=mongod --init-groups mongod --dbpath /data/db --bind_ip 127.0.0.1 --port 27017 &
  pid=$!
  trap 'kill "$pid" 2>/dev/null || true; wait "$pid" || true' EXIT
  ready=false
  for attempt in {1..60}; do
    if mongosh --quiet --host 127.0.0.1 --eval 'quit(db.adminCommand({ping:1}).ok ? 0 : 1)' >/dev/null 2>&1; then ready=true; break; fi
    sleep 1
  done
  [ "$ready" = true ] || exit 1
  mongosh --quiet --host 127.0.0.1 /usr/local/lib/mongo-init.js
  kill "$pid"
  wait "$pid"
  trap - EXIT
  touch /data/db/.initialized
  chown mongod:mongod /data/db/.initialized
fi
exec setpriv --reuid=mongod --regid=mongod --init-groups mongod --config /run/config/mongod.json
