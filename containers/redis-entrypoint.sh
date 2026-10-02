#!/bin/bash
set -euo pipefail
if [ "${TLS_ENABLED:-false}" = true ]; then
  mkdir -p /run/service-tls
  cp /run/tls/* /run/service-tls/
  chown -R redis:redis /run/service-tls
  chmod 700 /run/service-tls
fi
chown -R redis:redis /data
exec setpriv --reuid=redis --regid=redis --init-groups redis-server /run/config/redis.conf
