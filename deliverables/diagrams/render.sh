#!/usr/bin/env bash
# Render every Mermaid diagram in this folder to .svg and .png (white background).
# Diagrams render at natural size (not squeezed into the 800 px default viewport),
# so every PNG is about 2000 px wide or more and its text stays legible.
# Usage: bash deliverables/diagrams/render.sh
set -euo pipefail

MMDC_VERSION="12.2.0"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Headless Chromium needs --no-sandbox on many Linux hosts and in CI containers.
PUPPETEER_CONFIG="$(mktemp)"
MERMAID_CONFIG="$(mktemp)"
trap 'rm -f "$PUPPETEER_CONFIG" "$MERMAID_CONFIG"' EXIT
echo '{"args":["--no-sandbox"]}' > "$PUPPETEER_CONFIG"
echo '{"flowchart":{"useMaxWidth":false},"stateDiagram":{"useMaxWidth":false}}' > "$MERMAID_CONFIG"

shopt -s nullglob
sources=("$DIR"/*.mmd)
if [ ${#sources[@]} -eq 0 ]; then
  echo "No .mmd files found in $DIR" >&2
  exit 1
fi

for src in "${sources[@]}"; do
  base="${src%.mmd}"
  for ext in svg png; do
    npx -y "@mermaid-js/mermaid-cli@${MMDC_VERSION}" --quiet \
      --puppeteerConfigFile "$PUPPETEER_CONFIG" --configFile "$MERMAID_CONFIG" \
      --input "$src" --output "$base.$ext" \
      --backgroundColor white
  done
  echo "rendered $(basename "$base").{svg,png}"
done
