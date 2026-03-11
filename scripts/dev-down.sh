#!/usr/bin/env bash
set -euo pipefail

docker compose -f "$(dirname "$0")/../infra/docker-compose.yml" down
