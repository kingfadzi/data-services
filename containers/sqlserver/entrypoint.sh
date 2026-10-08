#!/bin/bash
# Start SQL Server, apply the mounted init scripts once each, then hand the container over to the
# engine. Ported from lean-infrastructure/docker/sqlserver/entrypoint.sh; the readiness streak and
# the per-script retries are there for "script upgrade mode" (see the comments below), not padding.
set -e

# The image has no MSSQL_SA_PASSWORD_FILE, so read the staged secret here rather than passing the
# password through the environment, where `docker inspect` would show it.
export MSSQL_SA_PASSWORD="$(cat /run/secrets/sqlserver_sa_password)"
DB=${SQLSERVER_DB:-appdb}
USERNAME=${SQLSERVER_USERNAME:-app}

/opt/mssql/bin/sqlservr &
SQLSERVER_PID=$!

SQLCMD="/opt/mssql-tools18/bin/sqlcmd -C"
if [ ! -f /opt/mssql-tools18/bin/sqlcmd ]; then
    SQLCMD="/opt/mssql-tools/bin/sqlcmd"
fi

# Wait for SQL Server to fully accept logins (past "script upgrade mode").
# After an engine package upgrade, sa logins are rejected for a while even
# though the listener accepts connections. Require N consecutive successes,
# spaced out, before declaring readiness.
echo "Waiting for SQL Server to start..."
ready_streak=0
required_streak=5
for i in {1..180}; do
    if $SQLCMD -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -Q "SELECT 1" -b &>/dev/null; then
        ready_streak=$((ready_streak + 1))
        if [ "$ready_streak" -ge "$required_streak" ]; then
            echo "SQL Server is ready (streak=$ready_streak after ${i}s)."
            break
        fi
    else
        ready_streak=0
    fi
    sleep 2
done

if [ "$ready_streak" -lt "$required_streak" ]; then
    echo "ERROR: SQL Server did not become ready in time." >&2
    exit 1
fi

# Per-script markers so newly added init scripts run on existing volumes.
INIT_DIR="/var/opt/mssql/.init-done"
mkdir -p "$INIT_DIR"

# Run a sqlcmd script with retries — survives transient "script upgrade mode"
# windows that can re-appear right after the engine signals ready.
run_sql_with_retry() {
    local file="$1"
    local attempts=10
    local delay=5
    for attempt in $(seq 1 $attempts); do
        if $SQLCMD -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -b \
             -v DB="$DB" USERNAME="$USERNAME" PASSWORD="$(cat /run/secrets/sqlserver_password)" \
             -i "$file"; then
            return 0
        fi
        echo "  attempt $attempt/$attempts failed, retrying in ${delay}s..."
        sleep "$delay"
    done
    return 1
}

for f in /docker-entrypoint-initdb.d/*.sql; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    if [ -f "$INIT_DIR/$name" ]; then
        echo "Skipping $name (already applied)."
        continue
    fi
    echo "Running $name..."
    if ! run_sql_with_retry "$f"; then
        echo "ERROR: $name failed after retries." >&2
        exit 1
    fi
    touch "$INIT_DIR/$name"
done
echo "Initialization complete."

# Verify FTS independently of the init scripts: on a volume where 02-fulltext-catalog.sql already
# ran, only this check would notice the image being rebuilt without the FTS package.
FTS_INSTALLED=$($SQLCMD -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -h -1 -W \
    -Q "SET NOCOUNT ON; SELECT CAST(SERVERPROPERTY('IsFullTextInstalled') AS INT)" 2>/dev/null | head -n1 | tr -d '[:space:]')
if [ "$FTS_INSTALLED" != "1" ]; then
    echo "ERROR: Full-Text Search is NOT installed (IsFullTextInstalled=$FTS_INSTALLED); rebuild with ./datactl build." >&2
    exit 1
fi
echo "Full-Text Search: installed."

wait $SQLSERVER_PID
