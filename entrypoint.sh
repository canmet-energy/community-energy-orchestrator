#!/bin/bash
set -e

# Ensure mounted volume directories are writable by appuser (UID 1000).
# When host directories are mounted via docker-compose, they may be owned by
# root or a different UID, causing permission errors for the non-root appuser.

# If running as root (e.g. docker-compose overrides user), fix permissions
# and drop to appuser. Otherwise just verify and run directly.
if [ "$(id -u)" = '0' ]; then
    for dir in /app/communities /app/output /app/logs; do
        if [ -d "$dir" ] && [ ! -w "$dir" ]; then
            chown appuser:appuser "$dir" 2>/dev/null || true
        fi
    done
    # Drop privileges using setpriv (built into util-linux, no extra dependencies)
    exec setpriv --reuid=1000 --regid=1000 --init-groups "$@"
fi

# Already running as appuser — just exec the command
exec "$@"
