#!/bin/bash
set -euo pipefail
if [ "${TLS_ENABLED:-false}" = true ]; then
  mkdir -p "$ES_PATH_CONF/tls"
  cp /run/tls/* "$ES_PATH_CONF/tls"/
  chown -R elasticsearch:elasticsearch "$ES_PATH_CONF/tls"
  chmod 700 "$ES_PATH_CONF/tls"
fi
cp /run/config/elasticsearch.yml "$ES_PATH_CONF/elasticsearch.yml"
# Keystore is image-local; bootstrap secret is stable across container replacement.
if [ ! -f "$ES_PATH_CONF/elasticsearch.keystore" ]; then
  /usr/share/elasticsearch/bin/elasticsearch-keystore create
fi
cat /run/secrets/elastic_password | /usr/share/elasticsearch/bin/elasticsearch-keystore add -x -f bootstrap.password
chown -R elasticsearch:elasticsearch "$ES_PATH_CONF" /usr/share/elasticsearch/data /usr/share/elasticsearch/logs
exec setpriv --reuid=elasticsearch --regid=elasticsearch --init-groups /usr/share/elasticsearch/bin/elasticsearch
