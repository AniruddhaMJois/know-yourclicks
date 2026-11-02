#!/usr/bin/env bash
# KnowYourClicks Status Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=== KnowYourClicks Daemon Status ==="
./knowyourclicks status
echo ""
./knowyourclicks stats
