#!/usr/bin/env bash
# Runs the Tailwind standalone CLI (no Node needed), downloading a pinned,
# checksum-verified binary into .bin/ on first use.
#   ./scripts/tailwind.sh            build minified CSS once
#   ./scripts/tailwind.sh --watch    rebuild on template changes (development)
set -euo pipefail

VERSION="v4.1.11"
cd "$(dirname "$0")/.."

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  asset="tailwindcss-macos-arm64" ;;
  Darwin-x86_64) asset="tailwindcss-macos-x64" ;;
  Linux-x86_64)  asset="tailwindcss-linux-x64" ;;
  Linux-aarch64) asset="tailwindcss-linux-arm64" ;;
  *) echo "Unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

bin=".bin/tailwindcss-$VERSION"
if [[ ! -x "$bin" ]]; then
  mkdir -p .bin
  base="https://github.com/tailwindlabs/tailwindcss/releases/download/$VERSION"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL --http1.1 --retry 5 --retry-all-errors -o "$tmp/$asset" "$base/$asset"
  curl -fsSL --http1.1 --retry 5 --retry-all-errors -o "$tmp/sha256sums.txt" "$base/sha256sums.txt"
  expected=$(grep -E " (\./)?$asset\$" "$tmp/sha256sums.txt" | awk '{print $1}' || true)
  actual=$(shasum -a 256 "$tmp/$asset" | awk '{print $1}')
  if [[ -z "$expected" || "$expected" != "$actual" ]]; then
    echo "Checksum mismatch for $asset (expected '$expected', got '$actual')" >&2
    exit 1
  fi
  install -m 755 "$tmp/$asset" "$bin"
fi

if [[ "${1:-}" == "--watch" ]]; then
  exec "$bin" -i static/src/app.css -o static/css/app.css --watch
else
  exec "$bin" -i static/src/app.css -o static/css/app.css --minify
fi
