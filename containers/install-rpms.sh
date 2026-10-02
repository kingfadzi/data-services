#!/bin/sh
set -eu
# No existing mirrorlist or public repository remains enabled.
rm -f /etc/yum.repos.d/*.repo
cp /run/secrets/yum_repo /etc/yum.repos.d/internal.repo
if command -v dnf >/dev/null; then
    dnf -y install "$@"
    dnf clean all
else
    microdnf -y install "$@"
    microdnf clean all
fi
rm -f /etc/yum.repos.d/internal.repo
