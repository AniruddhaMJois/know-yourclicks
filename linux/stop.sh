#!/usr/bin/env bash
# KnowYourClicks Stop Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

./knowyourclicks stop
