#!/usr/bin/env bash
# web 构建验证（web-easel-alignment 起）：tsc 严格 + vite build
set -euo pipefail
cd "$(dirname "$0")/../apps/web"
npm run build
