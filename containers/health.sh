#!/bin/bash
set -euo pipefail
case "$1" in
  elasticsearch)
    curl --fail --silent --config /run/config/elastic-health.conf >/dev/null ;;
  mongo)
    mongosh --quiet --nodb --eval '
      const fs = require("fs");
      const c = JSON.parse(fs.readFileSync("/run/secrets/mongo_credentials", "utf8"));
      const options = process.env.TLS_ENABLED === "true" ? "&tls=true&tlsCAFile=/run/tls/ca.pem" : "";
      const conn = new Mongo("mongodb://" + encodeURIComponent(c.username) + ":" + encodeURIComponent(c.password) + "@localhost:27017/admin?authSource=admin" + options);
      quit(conn.getDB("admin").runCommand({ping:1}).ok ? 0 : 1);' >/dev/null ;;
  redis)
    export REDISCLI_AUTH="$(cat /run/secrets/redis_password)"
    options=()
    if [ "${TLS_ENABLED:-false}" = true ]; then options=(--tls --cacert /run/tls/ca.pem); fi
    test "$(redis-cli "${options[@]}" ping)" = PONG ;;
esac
