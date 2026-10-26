#!/usr/bin/env bash
# KnowYourClicks Startup Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=== KnowYourClicks (Linux) ==="
./knowyourclicks app
