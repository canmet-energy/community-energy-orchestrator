#!/bin/bash
set -e

# Ensure mounted volume directories are writable by appuser (UID 1000).
# When host directories are mounted via docker-compose, they may be owned by
# root or a different UID, causing permission errors for the non-root appuser.

# If running as root (e.g. docker-compose overrides user), fix permissions
# and drop to appuser. Otherwise just verify and run directly.
if [ "$(id -u)" = '0' ]; then
    for dir in /app/output /app/logs /app/data/source-archetypes; do
        # Create directory if it doesn't exist
        mkdir -p "$dir" 2>/dev/null || true
        # Fix ownership if not already owned by UID 1000
        if [ -d "$dir" ]; then
            current_owner=$(stat -c '%u' "$dir" 2>/dev/null || echo "unknown")
            if [ "$current_owner" != "1000" ]; then
                echo "Fixing ownership of $dir (owner: $current_owner -> 1000)"
                chown -R 1000:1000 "$dir" 2>/dev/null || true
            fi
        fi
    done
    # Drop privileges using setpriv (built into util-linux, no extra dependencies)
    # Set HOME so tools find binaries installed in /app/.local/ (e.g. OpenStudio)
    export HOME=/app
    exec setpriv --reuid=1000 --regid=1000 --init-groups "$@"
fi

# Already running as appuser — just exec the command
exec "$@"
